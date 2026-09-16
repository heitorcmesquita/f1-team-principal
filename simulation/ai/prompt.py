"""Prompt builder for the LLM decision engine.

Builds one compact request per lap covering *all* AI drivers at once (batching),
so a full race triggers only a handful of calls. Nothing but game state goes
into the prompt — no user data, no secrets.
"""

from simulation.race import TYRE_RULES, DRY_START, normalize_tyre

TASK_EVENT = (
    "You are the race-strategy engineer for every AI team in a Formula 1 "
    "simulation. Decide, for each listed driver, whether they pit this lap and "
    "which compound they fit."
)

RULES = (
    "Ground rules: (1) a pit loses about {pit_loss}s plus a warm-up cost, so only "
    "pit when it clearly helps the race; (2) a tyre past its wear limit "
    "(" + ", ".join(f"{c} ~{TYRE_RULES[c]['wear_limit']} laps" for c in TYRE_RULES) + ") "
    "must be changed; (3) swaps are mandatory when the compound is clearly wrong "
    "for the track wetness (Intermediate 6-30, Wet 31+); (4) Safety Car = a cheap "
    "pit window; (5) in dry races every driver must use two different dry "
    "compounds (Soft/Medium/Hard); (6) cars 'positioned' as other teams are not "
    "yours — do not plan pit stops for the player's own cars (their drivers are "
    "excluded)."
)

OUTPUT_INSTRUCTIONS = (
    "Respond with a single JSON object in this EXACT structure:\n"
    '{"decisions":[{"driver": "<driver name>", "action": "pit"|"stay", '
    '"tyre": "<soft|medium|hard|intermediate|wet>", '
    '"reason": "<one short phrase>"}]}\n'
    "Include exactly one entry per driver in the list. Use action \"stay\" when "
    "no stop is warranted, tyre \"\" in that case. Tyre must be one of "
    "soft|medium|hard|intermediate|wet. Reasons are shown to players, keep them "
    "natural."
)


def build_system_prompt() -> str:
    return "\n".join([TASK_EVENT, RULES, OUTPUT_INSTRUCTIONS])


def build_user_payload(race_state) -> dict:
    """Compact per-lap snapshot of every running car for the LLM."""
    circuit = race_state["circuit"]
    laps_remaining = max(0, circuit.laps - race_state["lap"])
    is_dry_race = not race_state.get("wet_race_declared", False)

    running = [s for s in race_state["states"] if s["status"] == "Running"]
    leader_time = min((s["total_time"] for s in running), default=0.0)
    ordered = sorted(running, key=lambda s: (s.get("position") or 999, s["total_time"]))

    drivers = []
    for s in ordered:
        row = {
            "driver": s["driver"].name,
            "team": s["driver"].team.name,
            "position": s.get("position"),
            "tyre": normalize_tyre(s["tyre"]),
            "tyre_age": s["tyre_age"],
            "laps_on_current_tyre": s["tyre_age"],
            "compounds_used": sorted(set(s.get("compounds_used", []))),
            "pit_stops": s.get("pit_stops", 0),
            "gap_to_leader_seconds": round(s["total_time"] - leader_time, 3),
            "mandatory_second_compound_needed": bool(
                is_dry_race and len(set(s.get("compounds_used", [])) & set(DRY_START)) < 2
            ),
        }
        persona = race_state.get("team_personas", {}).get(s["driver"].team.id)
        if persona:
            row["team_style"] = {
                "risk": round(persona.get("risk_tolerance", 1.0), 2),
                "stint_extension": round(persona.get("stint_bias", 0.0), 2),
            }
        drivers.append(row)

    return {
        "race": {
            "lap": race_state["lap"],
            "laps_remaining": laps_remaining,
            "total_laps": circuit.laps,
            "weather": race_state.get("weather", ""),
            "track_wetness": round(race_state.get("track_wetness", 0.0), 1),
            "safety_car_deployed": bool(race_state.get("safety_car", False)),
            "red_flag": bool(race_state.get("red_flag_stoppage", False)),
            "pit_stop_cost_seconds": getattr(circuit, "pit_loss", 22.0),
            "dry_race": bool(is_dry_race),
        },
        "drivers": drivers,
    }