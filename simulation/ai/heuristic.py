"""The historical in-game AI strategy engine, ported verbatim.

This is the reference implementation (and the automatic fallback for the LLM
engine). The five functions here were moved out of ``simulation.race`` without
behavior changes:

- ``HeuristicEngine.pit_plan``  - was ``_apply_ai_strategy``
- ``_ai_pit_decision``         - unchanged
- ``_choose_pit_tyre``         - unchanged
- ``_pit_benefit``             - unchanged
- ``_predict_rejoin_traffic``  - unchanged
- ``HeuristicEngine.decide_run2`` - was ``_decide_run2`` in ``simulation.qualifying``

They share the pace/degradation/weather helpers that remain in
``simulation.race``.
"""

import random
from typing import List

from simulation.ai.base import PitDecision
from simulation.race import (
    DRY_START,
    NORMAL_PIT_LOSS,
    SC_PIT_LOSS,
    TYRE_RULES,
    TYRE_CLIFF_DEG,
    TYRE_WARMUP_COST,
    MEDIUM_DEG_REFERENCE,
    SAFETY_CAR_WEAR_MULTIPLIER,
    DRY_WETNESS,
    WET_WETNESS,
    normalize_tyre,
    tyre_label,
    projected_pace,
    _tyre_degradation,
    _stint_time_loss,
    _wet_penalty,
    _best_tyre_for_conditions,
)

# Tactical constants (moved verbatim from simulation.race).
PIT_GAIN_MARGIN = 3.0
WEATHER_SWAP_PENALTY = 1.6
WEATHER_DRYING_SWAP_PENALTY = 0.25
UNDERCUT_GAP_THRESHOLD = 3.0
UNDERCUT_RIVAL_WEAR_RATIO = 0.55
UNDERCUT_MIN_TYRE_AGE = 5
COVER_GAP_THRESHOLD = 3.0
COVER_MIN_TYRE_AGE = 4
SC_PIT_MIN_AGE_RATIO = 0.45
SC_PIT_LOSS_TOLERANCE = 8.0


class HeuristicEngine:
    """The original AI: tyre cliff, undercut, cover, mandated compounds,
    weather swaps and Safety-Car windows, personified by team risk profiles."""

    name = "heuristic"

    def pit_plan(self, race_state, events, rng=None) -> List[PitDecision]:
        rng = rng or random
        laps_remaining = max(0, race_state["circuit"].laps - race_state["lap"])
        safety_car = race_state["safety_car"]
        personas = race_state["team_personas"]
        running_sorted = sorted(
            [s for s in race_state["states"] if s["status"] == "Running"],
            key=lambda s: s["total_time"],
        )
        position_index = {s["driver"].name: i for i, s in enumerate(running_sorted)}
        is_dry_race = not race_state.get("wet_race_declared", False)
        pit_loss = getattr(race_state["circuit"], "pit_loss", NORMAL_PIT_LOSS)
        sc_pit_loss = SC_PIT_LOSS

        decisions = []

        # Iterate from the back of the field so a car's pit intent is known when
        # the car ahead of it evaluates the tactical "cover" reaction.
        for state in reversed(running_sorted):
            if state["driver"].team.id == race_state["player_team"].id or state["status"] != "Running" or state["pit_pending"]:
                continue
            persona = personas.get(state["driver"].team.id, {"risk_tolerance": 1.0, "hesitation": 0.25, "stint_bias": 0.0})
            tyre = normalize_tyre(state["tyre"])

            # Check mandatory 2-dry-compound rule requirement
            dry_used = set(state.get("compounds_used", [])) & set(DRY_START)
            needs_mandatory_compound = (
                is_dry_race
                and len(dry_used) < 2
                and laps_remaining <= max(8, int(race_state["circuit"].laps * 0.35))
                and state["tyre_age"] >= 4
            )

            # Weather: a tyre that is clearly the wrong choice must be swapped
            # immediately. On a drying track the AI also leaves the wets/inters.
            wet_penalty = _wet_penalty(race_state["track_wetness"], tyre)
            needs_weather_swap = wet_penalty >= WEATHER_SWAP_PENALTY
            if not needs_weather_swap and tyre in ("intermediate", "wet"):
                best = _best_tyre_for_conditions(race_state["track_wetness"])
                if best != tyre and wet_penalty >= WEATHER_DRYING_SWAP_PENALTY:
                    needs_weather_swap = True
            if needs_weather_swap:
                state["pit_pending"] = _best_tyre_for_conditions(race_state["track_wetness"])
                message = f"{state['driver'].name} pits for {tyre_label(state['pit_pending'])} in changing conditions."
                events.append(message)
                decisions.append(
                    PitDecision(driver=state["driver"].name, action="pit", tyre=state["pit_pending"], reason=message)
                )
                continue

            if needs_mandatory_compound:
                unused = [t for t in DRY_START if t not in dry_used]
                state["pit_pending"] = unused[0] if unused else _best_tyre_for_conditions(race_state["track_wetness"])
                message = f"{state['driver'].name} pits to meet the 2-compound mandatory tyre rule."
                events.append(message)
                decisions.append(
                    PitDecision(driver=state["driver"].name, action="pit", tyre=state["pit_pending"], reason=message)
                )
                continue

            idx = position_index.get(state["driver"].name)
            ahead = running_sorted[idx - 1] if idx is not None and idx > 0 else None
            behind = running_sorted[idx + 1] if idx is not None and idx + 1 < len(running_sorted) else None

            pit_tyre = _choose_pit_tyre(state, race_state, laps_remaining, pit_loss)
            should_pit, reason = _ai_pit_decision(
                state,
                race_state,
                pit_tyre,
                persona,
                ahead,
                behind,
                pit_loss=pit_loss,
                sc_pit_loss=sc_pit_loss,
            )
            if not should_pit:
                continue
            if rng.random() < persona["hesitation"]:
                continue
            state["pit_pending"] = pit_tyre
            if reason:
                events.append(reason)
            else:
                events.append(f"{state['driver'].name} is pitting for {tyre_label(pit_tyre)}.")
            decisions.append(
                PitDecision(driver=state["driver"].name, action="pit", tyre=pit_tyre, reason=reason)
            )

        return decisions

    # -- verbatim helpers (moved from simulation.race / simulation.qualifying) --

    def decide_run2(self, qual, driver_name) -> bool:
        entry = qual["entries"][driver_name]
        if entry["best_lap"] is None:
            return True
        from simulation.qualifying import _classification

        order = _classification(qual)
        total = len(order)
        pos = order.index(driver_name) if driver_name in order else total
        at_risk = pos >= total * 0.5
        if at_risk:
            return random.random() < 0.9
        circuit = qual["circuit"]
        pace = projected_pace(entry["driver"], circuit, "soft")
        field = [
            projected_pace(qual["entries"][n]["driver"], circuit, "soft")
            for n in qual["active_names"]
            if n != driver_name
        ]
        avg = sum(field) / max(1, len(field))
        chance = 0.45 - max(0.0, (avg - pace)) * 0.35
        return random.random() < max(0.10, min(0.45, chance))


# --------------------------------------------------------------------------- #
# Verbatim decision helpers moved from simulation.race
# --------------------------------------------------------------------------- #
def _ai_pit_decision(state, race_state, pit_tyre, persona=None, ahead=None, behind=None, pit_loss=NORMAL_PIT_LOSS, sc_pit_loss=None):
    """Decide whether an AI driver should pit this lap.

    Combines tyre cliff detection, tactical undercuts/covers, Safety Car windows
    and a simple expected-total-race-time comparison so teams never pit at a
    fixed tyre age.
    """
    persona = persona or {"risk_tolerance": 1.0, "hesitation": 0.25, "stint_bias": 0.0}
    risk = persona.get("risk_tolerance", 1.0)
    stint_bias = persona.get("stint_bias", 0.0)
    laps_remaining = max(0, race_state["circuit"].laps - race_state["lap"])
    if laps_remaining <= 2:
        return False, None
    tyre = normalize_tyre(state["tyre"])
    age = state["tyre_age"]
    info = TYRE_RULES.get(tyre, TYRE_RULES["medium"])
    limit = info["wear_limit"]
    wear_mult = SAFETY_CAR_WEAR_MULTIPLIER if race_state["safety_car"] else 1.0
    deg_now = _tyre_degradation(age, info["deg"], limit, wear_mult)
    deg_scale = info["deg"] / MEDIUM_DEG_REFERENCE

    # Aggressive teams (and positive stint bias) stretch their tyres further.
    # The cliff is compound-aware: softer compounds fall off before harder ones
    # relative to their own wear limit.
    cliff = TYRE_CLIFF_DEG * deg_scale * (0.6 + 0.4 * risk) * (1 + 0.15 * stint_bias)

    # Undercut: only with a heavily worn rival ahead, a clearly faster fresh tyre
    # and a clean-air rejoin. Otherwise the advantage is cancelled by traffic.
    undercut = False
    if ahead is not None and not race_state["safety_car"]:
        ahead_tyre = normalize_tyre(ahead.get("tyre", "medium"))
        ahead_info = TYRE_RULES.get(ahead_tyre, TYRE_RULES["medium"])
        ahead_limit = ahead_info["wear_limit"]
        ahead_age = ahead.get("tyre_age", 0)
        ahead_deg = _tyre_degradation(ahead_age, ahead_info["deg"], ahead_limit, wear_mult)
        gap = max(0.0, state["total_time"] - ahead["total_time"])
        my_pace = projected_pace(state["driver"], race_state["circuit"], pit_tyre)
        rival_pace = projected_pace(ahead["driver"], race_state["circuit"], ahead_tyre) + ahead_deg
        if (
            gap < UNDERCUT_GAP_THRESHOLD
            and ahead_age >= ahead_limit * UNDERCUT_RIVAL_WEAR_RATIO
            and ahead_deg >= TYRE_CLIFF_DEG * 0.8 * (ahead_info["deg"] / MEDIUM_DEG_REFERENCE)
            and age >= UNDERCUT_MIN_TYRE_AGE
            and my_pace <= rival_pace - 0.15
            and _predict_rejoin_traffic(state, race_state, pit_tyre, pit_loss) == 0
        ):
            undercut = True

    # Cover: a close rival behind is pitting. Decisions are evaluated from the
    # back of the field, so the rival's pit intent is already known here.
    cover = (
        behind is not None
        and behind.get("pit_pending")
        and max(0.0, behind["total_time"] - state["total_time"]) < COVER_GAP_THRESHOLD
        and age >= COVER_MIN_TYRE_AGE
    )

    pit = False
    reason = None
    if deg_now >= cliff:
        pit = True
        reason = f"{state['driver'].name} pits, {tyre_label(tyre)} tyres are past their best."
    elif undercut:
        pit = True
        reason = f"{state['driver'].name} pits early to try an undercut on {ahead['driver'].name}."
    elif cover:
        pit = True
        reason = f"{state['driver'].name} reacts and covers the pit stop."
    elif race_state["safety_car"] and age >= limit * SC_PIT_MIN_AGE_RATIO:
        # The pack is compressed, so a stop under the Safety Car is relatively
        # cheap (only a fraction of the usual pit loss counts). Take it when the
        # fresh set is roughly worth it.
        benefit = _pit_benefit(state, race_state, pit_tyre, laps_remaining, pit_loss=sc_pit_loss if sc_pit_loss is not None else pit_loss)
        if benefit > -SC_PIT_LOSS_TOLERANCE * risk:
            pit = True
            reason = f"{state['driver'].name} takes the opportunity to pit under the Safety Car."
    elif deg_now >= TYRE_CLIFF_DEG * 0.6 * deg_scale and laps_remaining > 6:
        # Voluntary strategy stop: only when a fresh set clearly saves time over the rest.
        benefit = _pit_benefit(state, race_state, pit_tyre, laps_remaining, pit_loss=pit_loss)
        if benefit > PIT_GAIN_MARGIN * risk:
            pit = True
            reason = f"{state['driver'].name} pits for a fresh set of {tyre_label(pit_tyre)}."

    if not pit:
        return False, None

    # Overcut/stretch: deterministically hold the stop when pitting would drop
    # the driver into traffic — stretching the stint keeps clean air.
    if not undercut and not cover and not race_state["safety_car"]:
        if _predict_rejoin_traffic(state, race_state, pit_tyre, pit_loss) > 0:
            return False, None
    return True, reason


def _pit_benefit(state, race_state, pit_tyre, laps_remaining, pit_loss=NORMAL_PIT_LOSS):
    """Expected seconds saved by pitting now versus stretching the current set
    to its wear limit and pitting then.

    Positive means pitting now is faster. The fresh set is only priced over the
    distance it would actually cover, so a mid-race stop is not penalised by the
    current set's cliff degradation as if it kept running to the flag.
    """
    tyre = normalize_tyre(state["tyre"])
    info = TYRE_RULES.get(tyre, TYRE_RULES["medium"])
    age = state["tyre_age"]
    limit = info["wear_limit"]
    new_info = TYRE_RULES.get(pit_tyre, TYRE_RULES["medium"])
    laps_left = max(0, int(laps_remaining))
    if laps_left <= 0:
        return 0.0

    pace_delta = (info["pace"] - new_info["pace"]) * laps_left
    stay_laps = min(laps_left, max(0, limit - age))

    if stay_laps >= laps_left:
        # The current set survives to the flag: one stop either way.
        stay_cost = _stint_time_loss(age, info["deg"], limit, laps_left)
        stop_cost = TYRE_WARMUP_COST + _stint_time_loss(0, new_info["deg"], new_info["wear_limit"], laps_left)
    else:
        # Otherwise staying out means a stop at the cliff plus a fresh stint.
        fresh_laps = laps_left - stay_laps
        stay_cost = (
            _stint_time_loss(age, info["deg"], limit, stay_laps)
            + pit_loss
            + TYRE_WARMUP_COST
            + _stint_time_loss(0, new_info["deg"], new_info["wear_limit"], fresh_laps)
        )
        stop_cost = TYRE_WARMUP_COST + _stint_time_loss(0, new_info["deg"], new_info["wear_limit"], laps_left)

    return stay_cost - stop_cost - pit_loss + pace_delta


def _choose_pit_tyre(state, race_state, laps_remaining, pit_loss=NORMAL_PIT_LOSS):
    """Pick the compound that minimises estimated total race time.

    Balances compound speed against degradation over the distance left, plus the
    cost of any additional stops the compound would force (pit loss and warm-up
    cost per extra stop). The mandatory two-compound rule is enforced separately
    before this is consulted.
    """
    wetness = race_state["track_wetness"]
    if wetness > WET_WETNESS:
        return "wet"
    if wetness > DRY_WETNESS:
        return "intermediate"
    best = None
    best_cost = None
    for t in DRY_START:
        info = TYRE_RULES[t]
        limit = info["wear_limit"]
        # Complete stops the compound forces over the remaining distance.
        needed_stops = max(0, (laps_remaining - 1) // max(1, limit))
        pit_overhead = needed_stops * (pit_loss + TYRE_WARMUP_COST)
        loss = (
            TYRE_WARMUP_COST
            + _stint_time_loss(0, info["deg"], limit, laps_remaining)
            + info["pace"] * laps_remaining
            + pit_overhead
        )
        if best_cost is None or loss < best_cost:
            best_cost = loss
            best = t
    return best


def _predict_rejoin_traffic(state, race_state, new_tyre, pit_loss=NORMAL_PIT_LOSS):
    """Estimate how many cars a driver would rejoin behind after a pit stop.

    Returns the number of slower cars the fresh pace would likely be stuck behind.
    """
    pred_total = state["total_time"] + pit_loss
    my_pace = projected_pace(state["driver"], race_state["circuit"], new_tyre)
    traffic = 0
    for other in race_state["states"]:
        if other is state or other["status"] != "Running":
            continue
        if other.get("pit_pending"):
            continue
        gap = other["total_time"] - pred_total
        if -1.5 < gap < 3.0:
            other_tyre = normalize_tyre(other["tyre"])
            other_pace = projected_pace(other["driver"], race_state["circuit"], other_tyre)
            other_pace += _tyre_degradation(other["tyre_age"], TYRE_RULES[other_tyre]["deg"], TYRE_RULES[other_tyre]["wear_limit"], 1.0)
            if other_pace > my_pace - 0.4:
                traffic += 1
    return traffic