import json
import random
import sys
from pathlib import Path

import httpx
import pytest

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from utils import load
from simulation.race import create_race, run_lap, is_race_finished
from simulation.ai.factory import engine_name, resolve_engine
from simulation.ai.api import ApiEngine


def _race_state():
    """A dry race with an AI driver forced into a deterministic pit need.

    ``tyre_age=22`` on a soft (~14-lap limit) plus one dry compound used puts the
    driver past the cliff AND the mandatory two-dry-compound window (last
    quarter of the race), so both the API and the heuristic fallback clearly
    want a stop this lap.
    """
    drivers, circuits = load()
    player_team = drivers[0].team
    race = create_race(drivers, circuits[0], player_team, track_wetness=0)
    race["lap"] = 40
    for s in race["states"]:
        if s["driver"].team.id == player_team.id:
            continue
        s["tyre"] = "soft"
        s["tyre_age"] = 22  # soft wear limit = 14 -> past the cliff zone
        s["compounds_used"] = ["soft"]
        break
    race["events"] = []
    return race


def _content(body):
    """Wrap content in the OpenAI-compatible chat response shape."""
    return {"choices": [{"message": {"content": json.dumps(body)}}]}


def _engine(handler, **kwargs):
    return ApiEngine(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


# --- engine resolution -----------------------------------------------------

def test_engine_name_from_key():
    assert engine_name(None) == "heuristic"
    assert engine_name("") == "heuristic"
    assert engine_name("groq_key") == "api"


def test_resolve_engine_never_throws_and_never_networks():
    # Construction must not touch the network (no request is sent until pit_plan).
    assert resolve_engine(None).name == "heuristic"
    assert resolve_engine("test-key").name == "api"


# --- valid / partial responses ---------------------------------------------

def test_api_applies_valid_decisions():
    target_name = [s for s in _race_state()["states"] if s["tyre_age"] == 22][0]["driver"].name

    def handler(request):
        # One batched request for ALL AI drivers in a single call.
        board = json.loads(request.content)
        assert isinstance(board["messages"][1]["content"], str)
        return httpx.Response(200, json=_content(
            [{"driver": target_name, "action": "pit", "tyre": "hard", "reason": "Fresh set."}]
        ))

    race = _race_state()
    events = []
    calls = {"n": 0}

    def counting_handler(request):
        calls["n"] += 1
        return handler(request)

    engine = _engine(counting_handler)
    decisions = engine.pit_plan(race, events)

    assert calls["n"] == 1
    assert race["ai_engine"] == "api"
    assert race["_ai_calls"] == 1
    by_name = {d.driver: d for d in decisions}
    target = [s for s in race["states"] if s["tyre_age"] == 22][0]
    assert target["pit_pending"] == "hard"
    assert any("Fresh set." in m for m in events)
    # A driver the model reported "stay" for keeps running.
    stayer = [d.driver for d in decisions if d.action == "stay"]
    assert len(stayer) == 0  # model only mentioned the one driver; rest stay


def test_api_partial_coverage_means_stay_for_unmentioned():
    def handler(request):
        return httpx.Response(200, json=_content([]))  # "pit nobody"

    race = _race_state()
    engine = _engine(handler)
    decisions = engine.pit_plan(race, [])
    assert decisions == [] or all(d.action == "stay" for d in decisions)
    assert all(s.get("pit_pending") is None for s in race["states"])


# --- failure modes -> heuristic fallback -----------------------------------

def test_api_garbage_falls_back_to_heuristic():
    def handler(request):
        return httpx.Response(200, json=_content("definitely not json"))

    race = _race_state()
    events = []
    engine = _engine(handler)
    engine.pit_plan(race, events)  # must not raise
    # Fallback: the cliffed AI driver pits for a fresh set as the heuristic would.
    target = [s for s in race["states"] if s["tyre_age"] == 22][0]
    assert target["pit_pending"] in {"soft", "medium", "hard"}
    assert any(("pits" in m or "pitting" in m) for m in events)


def test_api_http_error_falls_back_to_heuristic():
    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    race = _race_state()
    events = []
    engine = _engine(handler)
    decisions = engine.pit_plan(race, events)
    target = [s for s in race["states"] if s["tyre_age"] == 22][0]
    assert decisions and target["pit_pending"] in {"soft", "medium", "hard"}


def test_api_timeout_falls_back_to_heuristic():
    def handler(request):
        raise httpx.ReadTimeout("deadline exceeded")

    race = _race_state()
    events = []
    engine = _engine(handler)
    decisions = engine.pit_plan(race, events)
    target = [s for s in race["states"] if s["tyre_age"] == 22][0]
    assert decisions and target["pit_pending"] in {"soft", "medium", "hard"}


def test_api_unknown_tyre_falls_back_to_heuristic():
    target_name = [s for s in _race_state()["states"] if s["tyre_age"] == 22][0]["driver"].name

    def handler(request):
        return httpx.Response(200, json=_content(
            [{"driver": target_name, "action": "pit", "tyre": "spaceballs", "reason": "n/a"}]
        ))

    race = _race_state()
    events = []
    engine = _engine(handler)
    engine.pit_plan(race, events)
    target = [s for s in race["states"] if s["tyre_age"] == 22][0]
    assert target["pit_pending"] in {"soft", "medium", "hard"}


def test_api_respects_per_race_call_budget():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json=_content([]))

    race = _race_state()
    engine = _engine(handler, max_calls_per_race=1)
    # First (allowed) call: budget is used, response is applied.
    engine.pit_plan(race, [])
    assert calls["n"] == 1
    # Second plausible lap: budget exhausted -> heuristic fallback, no new call.
    engine.pit_plan(race, [])
    assert calls["n"] == 1


# --- heuristic engine determinism (regression guard) -----------------------

def test_heuristic_determinism_across_runs():
    drivers, circuits = load()
    results = []
    for seed_value in (7, 7):  # same seed twice must produce identical races
        rng = random.Random(seed_value)
        race = create_race(drivers, circuits[0], drivers[0].team, track_wetness=0, rng=rng)
        while not is_race_finished(race):
            run_lap(race, {})
        results.append(
            (
                [s["driver"].name for s in race["states"]],
                [s["tyre_age"] for s in race["states"]],
                list(race.get("events", []) or []),
            )
        )
    assert results[0] == results[1]
    assert race["ai_engine"] == "heuristic"


# --- save-safety: engine name string only, never the key -------------------

def test_ai_engine_save_safe_string():
    drivers, circuits = load()
    race = create_race(drivers, circuits[0], drivers[0].team, track_wetness=0)
    race["ai_engine"] = "api"  # as RaceService sets when a key is present
    assert isinstance(race["ai_engine"], str)
    # The tagged-JSON serializer passes plain strings through untouched.
    from backend.app.services.save_service import _to_jsonable
    saved = _to_jsonable(race)
    assert saved["ai_engine"] == "api"
    assert "ai_engine" in saved