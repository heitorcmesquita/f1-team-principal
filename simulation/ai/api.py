"""OpenAI-compatible LLM decision engine.

One batched chat-completions call per lap covering all AI drivers, throttled to
the laps where a strategy decision is actually plausible. On any failure
(timeout, HTTP error, malformed JSON, invalid/unknown tyre) the engine falls
back to the heuristic for the affected lap so the race never throws and the
save game stays valid.
"""

import json
import logging
import os
from typing import List, Optional

import httpx

from simulation.ai.base import PitDecision
from simulation.ai.heuristic import HeuristicEngine, WEATHER_SWAP_PENALTY
from simulation.ai.prompt import build_system_prompt, build_user_payload
from simulation.race import (
    DRY_START,
    TYRE_RULES,
    VALID_TYRES,
    normalize_tyre,
    tyre_label,
    _wet_penalty,
)

logger = logging.getLogger("simulation.ai.api")

DEFAULT_RESPONSE_FORMAT = True  # {"type": "json_object"} (Groq/Gemini/Cerebras)


class ApiEngine:
    """DecisionEngine that calls an OpenAI-compatible chat-completions API.

    Kwargs override the ``AI_*`` environment variables so tests can inject a
    mocked transport and custom parameters without touching the environment.
    """

    name = "api"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_calls_per_race: Optional[int] = None,
        temperature: Optional[float] = None,
        transport=None,
    ):
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("AI_API_BASE") or "https://api.groq.com/openai/v1").rstrip("/")
        self.model = model or os.environ.get("AI_MODEL") or "llama-3.3-70b-versatile"
        self.timeout = float(timeout if timeout is not None else os.environ.get("AI_TIMEOUT", "10"))
        self.max_calls = int(max_calls_per_race if max_calls_per_race is not None else os.environ.get("AI_MAX_CALLS_PER_RACE", "60"))
        self.temperature = float(temperature if temperature is not None else os.environ.get("AI_TEMPERATURE", "0.2"))
        self.transport = transport

    # -- DecisionEngine interface -------------------------------------------

    def pit_plan(self, race_state, events, rng=None) -> List[PitDecision]:
        if not self._should_ask(race_state):
            return []
        if race_state.get("_ai_calls", 0) >= self.max_calls:
            logger.warning("AI engine: per-race call budget (%s) exhausted; using heuristic.", self.max_calls)
            return HeuristicEngine().pit_plan(race_state, events, rng)

        try:
            raw = self._chat(race_state)
            decisions = self._parse_and_apply(race_state, events, raw)
        except Exception as exc:  # timeout, HTTP, JSON, anything -> never throw
            # Failures still consume budget: a persistently broken endpoint
            # (e.g. timing out every lap) must not stall the whole race.
            race_state["_ai_calls"] = race_state.get("_ai_calls", 0) + 1
            logger.warning("AI engine failed (%s: %s); falling back to heuristic.", type(exc).__name__, exc)
            return HeuristicEngine().pit_plan(race_state, events, rng)

        race_state["_ai_calls"] = race_state.get("_ai_calls", 0) + 1
        race_state["ai_engine"] = self.name
        return decisions

    def decide_run2(self, qual, driver_name) -> bool:
        # Qualifying currently stays on the heuristic even with a key; the LLM
        # budget is spent on race strategy where the value is highest.
        return HeuristicEngine().decide_run2(qual, driver_name)

    # -- internals -----------------------------------------------------------

    def _should_ask(self, race_state) -> bool:
        """Throttle: only spend an API call when a decision is plausible.

        Triggers: safety car / red flag, a just-changing weather lap, a tyre in
        or past its wear cliff zone, a wrong-weather compound, or the mandatory
        two-dry-compound rule about to bite.
        """
        if race_state.get("safety_car") or race_state.get("red_flag_stoppage"):
            return True
        if race_state.get("weather_grace_laps", 0) > 0:
            return True

        wetness = race_state.get("track_wetness", 0.0)
        is_dry_race = not race_state.get("wet_race_declared", False)
        laps_remaining = max(0, race_state["circuit"].laps - race_state["lap"])
        player_team_id = race_state["player_team"].id if race_state.get("player_team") else None

        for s in race_state["states"]:
            if s["status"] != "Running" or s.get("pit_pending"):
                continue
            if player_team_id is not None and s["driver"].team.id == player_team_id:
                continue
            tyre = normalize_tyre(s["tyre"])
            info = TYRE_RULES.get(tyre, TYRE_RULES["medium"])
            if s["tyre_age"] >= info["wear_limit"] * 0.7:
                return True
            if _wet_penalty(wetness, tyre) >= WEATHER_SWAP_PENALTY:
                return True
            dry_used = set(s.get("compounds_used", [])) & set(DRY_START)
            if (
                is_dry_race
                and len(dry_used) < 2
                and laps_remaining <= max(8, int(race_state["circuit"].laps * 0.35))
                and s["tyre_age"] >= 4
            ):
                return True
        return False

    def _chat(self, race_state) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": json.dumps(build_user_payload(race_state))},
            ],
            "temperature": self.temperature,
            "max_tokens": 1200,
        }
        if DEFAULT_RESPONSE_FORMAT:
            body["response_format"] = {"type": "json_object"}
        with httpx.Client(transport=self.transport) as client:
            response = client.post(url, headers=headers, json=body, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_and_apply(self, race_state, events, raw: str) -> List[PitDecision]:
        """Parse the strict JSON response and apply the decisions.

        The whole payload is validated into a clean plan BEFORE anything is
        applied, so a malformed entry later in the list never leaves earlier
        drivers partially touched (the caller's whole-lap heuristic fallback
        then runs against pristine state). Drivers the model did not mention
        simply stay out.
        """
        try:
            entries = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"response is not JSON: {exc}") from exc
        if not isinstance(entries, list):
            raise ValueError("response is not a JSON array")

        plan = {}
        for ent in entries:
            if not isinstance(ent, dict):
                raise ValueError("decision entry is not an object")
            if not ent.get("driver"):
                raise ValueError("decision entry has no driver")
            action = str(ent.get("action", "stay")).strip().lower()
            if action not in ("stay", "pit"):
                raise ValueError(f"unknown action {action!r}")
            tyre = None
            if action == "pit":
                tyre = normalize_tyre(ent.get("tyre"))
                if tyre not in VALID_TYRES:
                    raise ValueError(f"unknown tyre {tyre!r}")
            plan[str(ent["driver"])] = (action, tyre, str(ent.get("reason") or "").strip())

        player_team_id = race_state["player_team"].id if race_state.get("player_team") else None
        applied = []
        for state in race_state["states"]:
            if state["status"] != "Running" or state.get("pit_pending"):
                continue
            if player_team_id is not None and state["driver"].team.id == player_team_id:
                continue
            entry = plan.get(state["driver"].name)
            if entry is None:
                continue  # not mentioned -> stay out
            action, tyre, reason = entry
            if action == "stay":
                continue
            if not reason:
                reason = f"{state['driver'].name} is pitting for {tyre_label(tyre)}."
            state["pit_pending"] = tyre
            events.append(reason)
            applied.append(PitDecision(driver=state["driver"].name, action="pit", tyre=tyre, reason=reason))
        return applied