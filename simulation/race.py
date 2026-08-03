import random

# --------------------------------------------------------------------------- #
# Tyre compounds
# --------------------------------------------------------------------------- #
# Each compound defines: pace (seconds faster than the hard reference), deg
# (degradation scale), wear_limit (laps until the tyre "cliff"), wet_low/high
# (track wetness window it suits) and dnf (per-race failure risk attributable
# to running the compound).
TYRE_RULES = {
    "soft": {"pace": -0.85, "deg": 1.9, "wear_limit": 14, "wet_low": 0, "wet_high": 5, "dnf": 0.0},
    "medium": {"pace": -0.45, "deg": 1.2, "wear_limit": 20, "wet_low": 0, "wet_high": 5, "dnf": 0.05},
    "hard": {"pace": 0.0, "deg": 0.8, "wear_limit": 26, "wet_low": 0, "wet_high": 5, "dnf": 0.08},
    "intermediate": {"pace": 0.35, "deg": 1.1, "wear_limit": 18, "wet_low": 6, "wet_high": 30, "dnf": 0.12},
    "wet": {"pace": 1.1, "deg": 1.0, "wear_limit": 20, "wet_low": 31, "wet_high": 100, "dnf": 0.18},
}
DRY_START = ("soft", "medium", "hard")
# Tyres used by the back half of the grid in dry conditions.
DRY_START_FIELD = ("medium", "hard")
# Front rows usually start on softs, but a driver will sometimes pick a
# different compound as a strategic call (e.g. a long opening stint on mediums).
DRY_FRONT_START = ("soft", "soft", "soft", "soft", "soft", "soft", "medium", "hard")
VALID_TYRES = set(TYRE_RULES)

# --------------------------------------------------------------------------- #
# Pit stops
# --------------------------------------------------------------------------- #
# Time lost during a pit stop. Circuits can override this via Circuit.pit_loss.
NORMAL_PIT_LOSS = 22.0
# A stop taken under the Safety Car is a fixed, discounted cost. The field is
# bunched anyway, so it is modelled as a flat 10s loss instead of the usual
# 22s green-flag stop.
SC_PIT_LOSS = 10.0

# Fresh tyres need a few laps to reach peak performance after a pit stop. The
# penalty decays every lap via TYRE_WARMUP_DECAY / TYRE_WARMUP_FLAT_DROP so the
# first laps of a stint are never the fastest.
TYRE_WARMUP_PENALTY = 2.2
TYRE_WARMUP_DECAY = 0.35
TYRE_WARMUP_FLAT_DROP = 0.15
# Total warm-up seconds lost across a fresh stint (used by AI cost estimates).
TYRE_WARMUP_COST = 2.9

# A voluntary stop must beat staying out by at least this many seconds to be worth it.
PIT_GAIN_MARGIN = 3.0

# --------------------------------------------------------------------------- #
# Safety Car / Red Flag
# --------------------------------------------------------------------------- #
SAFETY_CAR_WEAR_MULTIPLIER = 0.4
SAFETY_CAR_LAP_DELTA = 6.0
SAFETY_CAR_GAP_STEP = 0.5
SC_ACCIDENT_CHANCE = 0.6
SC_AQUAPLANE_CHANCE = 0.4
# A mechanical DNF can interrupt the race too (VSC/SC-style) at a modest chance,
# so the Safety Car system actually exercises in dry races.
SC_MECHANICAL_CHANCE = 0.35
SC_MIN_TIMER = 3
SC_MAX_TIMER = 6
RED_FLAG_ACCIDENTS = 2
RED_FLAG_SINGLE_CHANCE = 0.12
SC_AFTER_RED_FLAG_MIN = 2
SC_AFTER_RED_FLAG_MAX = 4

# --------------------------------------------------------------------------- #
# Traffic & overtaking
# --------------------------------------------------------------------------- #
TRAFFIC_PENALTY_PER_LAP = 0.18
TRAFFIC_PENALTY_CAP_LAPS = 5
TRAFFIC_OVERTAKE_BONUS_PER_LAP = 0.025
TRAFFIC_OVERTAKE_BONUS_CAP_LAPS = 5
OVERTAKE_BASE_CHANCE = 0.06
OVERTAKE_TALENT_FACTOR = 0.005
OVERTAKE_GAP_FACTOR = 0.02
OVERTAKE_LAP_ONE_BONUS = 0.12
OVERTAKE_MIN_CHANCE = 0.04
OVERTAKE_MAX_CHANCE = 0.6
# A chaser's pace edge in seconds this lap scales the pass probability, so a
# meaningful speed advantage is needed before a move becomes likely.
OVERTAKE_PACE_FACTOR = 0.5
# Below this projected pace edge (seconds) a pass attempt is not even made,
# suppressing the noise-driven back-and-forth that made races feel chaotic.
OVERTAKE_MIN_PACE = 0.18
# A pass is only attempted when the chaser starts the lap within this gap.
PASS_WINDOW = 0.9

# --------------------------------------------------------------------------- #
# Tyre degradation / weather
# --------------------------------------------------------------------------- #
# A tyre is "past its best" once per-lap degradation reaches this level. The
# absolute value is measured against a medium reference compound; in practice
# the threshold scales with each compound's own degradation rate so every
# compound hits the cliff near its wear limit.
TYRE_CLIFF_DEG = 0.9
MEDIUM_DEG_REFERENCE = 1.2
# Green-phase polynomial coefficients and post-limit fall-off.
DEG_GREEN_1 = 0.12
DEG_GREEN_2 = 0.30
DEG_GREEN_4 = 0.28
DEG_PAST_BASE = 0.70
DEG_PAST_SLOPE = 0.06
# Wet tyres on a dry track overheat and wear much faster.
WET_ON_DRY_WEAR_MULTIPLIER = 2.2

# Random per-lap pace noise plus a small persistent per-driver luck term. The
# luck term adds short-range autocorrelation so results don't drift like a
# pure random walk.
LAP_NOISE = 0.18
LAP_LUCK_SPREAD = 0.12
# Global wet slowdown in seconds per % track wetness.
WET_SLOWDOWN_PER_WETNESS = 0.02

# --------------------------------------------------------------------------- #
# Weather
# --------------------------------------------------------------------------- #
DRY_WETNESS = 5
WET_WETNESS = 30
RAIN_DRY_TO_LIGHT = 0.015
RAIN_LIGHT_TO_DRY = 0.08
RAIN_LIGHT_TO_HEAVY = 0.04
RAIN_HEAVY_TO_LIGHT = 0.10
RAIN_MAX_PROB = 0.95

# AI weather-swap thresholds.
WEATHER_SWAP_PENALTY = 1.6
WEATHER_DRYING_SWAP_PENALTY = 0.25

# --------------------------------------------------------------------------- #
# Persona / tactics
# --------------------------------------------------------------------------- #
PERSONA_RISK_MIN = 0.6
PERSONA_RISK_MAX = 1.6
PERSONA_HESITATION_MIN = 0.10
PERSONA_HESITATION_MAX = 0.40

UNDERCUT_GAP_THRESHOLD = 3.0
UNDERCUT_RIVAL_WEAR_RATIO = 0.55
UNDERCUT_MIN_TYRE_AGE = 5
COVER_GAP_THRESHOLD = 3.0
COVER_MIN_TYRE_AGE = 4

# Tactical pit behaviour under the Safety Car.
SC_PIT_MIN_AGE_RATIO = 0.45
SC_PIT_LOSS_TOLERANCE = 8.0

# --------------------------------------------------------------------------- #
# DNF / risk
# --------------------------------------------------------------------------- #
# Risk levels are displayed relative to each driver's RACE-level DNF chance.
RISK_LOW_THRESHOLD = 0.04
RISK_MEDIUM_THRESHOLD = 0.12

MECH_BASE = 0.02
MECH_RELIABILITY_FACTOR = 0.005
ACCIDENT_BASE = 0.006
ACCIDENT_DEG_FACTOR = 0.003
ACCIDENT_WET_FACTOR = 0.02
TYRE_DNF_WEIGHT = 0.1
ACCIDENT_MAX = 0.08
ACCIDENT_SKILL_FLOOR = 0.55
ACCIDENT_SKILL_BASE = 1.05
ACCIDENT_SKILL_TALENT = 0.012

TYRE_ALIAS_MAP = {
    "macio": "soft",
    "medio": "medium",
    "médio": "medium",
    "duro": "hard",
    "intermediario": "intermediate",
    "intermediário": "intermediate",
    "chuva": "wet",
    "soft": "soft",
    "medium": "medium",
    "hard": "hard",
    "intermediate": "intermediate",
    "wet": "wet",
}

# Dedicated RNG for Monte-Carlo forecasts so that asking for a forecast never
# perturbs the race's own random stream.
_FORECAST_RNG = random.Random()


def seed(value):
    """Seed the simulation's random generators for reproducible races/seasons."""
    random.seed(value)
    _FORECAST_RNG.seed(value)


def normalize_tyre(name):
    if not name:
        return "medium"
    cleaned = str(name).strip().lower()
    return TYRE_ALIAS_MAP.get(cleaned, cleaned)


def tyre_label(tyre_name):
    tyre_key = normalize_tyre(tyre_name)
    return {
        "soft": "Soft",
        "medium": "Medium",
        "hard": "Hard",
        "intermediate": "Intermediate",
        "wet": "Wet",
    }.get(tyre_key, str(tyre_name).capitalize())


def is_valid_tyre(name):
    return normalize_tyre(name) in VALID_TYRES


def initial_tyre(track_wetness, rng=None):
    rng = rng or random
    if track_wetness > WET_WETNESS:
        return "wet"
    if track_wetness > DRY_WETNESS:
        return "intermediate"
    return rng.choice(DRY_START)


def _pace_terms(driver, circuit):
    """Deterministic talent + car performance terms shared by all pace models."""
    talent = getattr(driver, "talent", 80)
    team = driver.team
    engine = getattr(team, "engine", 50)
    aero = getattr(team, "aerodynamics", 50)
    driver_gain = talent * 0.035
    car_gain = (engine * getattr(circuit, "engine_factor", 0.5) + aero * getattr(circuit, "aero_factor", 0.5)) * 0.022
    return driver_gain, car_gain


def projected_pace(driver, circuit, tyre="soft"):
    """Deterministic lap-time estimate (no noise) shared by race & qualifying logic."""
    tyre_key = normalize_tyre(tyre)
    tyre_info = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
    driver_gain, car_gain = _pace_terms(driver, circuit)
    return circuit.base_lap_time - driver_gain - car_gain + tyre_info["pace"]


def qualifying_lap_time(driver, circuit, track_wetness, tyre="soft", evolution_bonus=0.0, traffic_penalty=0.0, rng=None):
    """Single flying-lap time for qualifying. Mirrors the race pace model (fresh tyre, no pit/SC)."""
    rng = rng or random
    tyre_key = normalize_tyre(tyre)
    global_wet_slowdown = track_wetness * WET_SLOWDOWN_PER_WETNESS
    wet_penalty = _wet_penalty(track_wetness, tyre_key)
    noise = rng.gauss(0, LAP_NOISE)
    return projected_pace(driver, circuit, tyre) + global_wet_slowdown + wet_penalty + evolution_bonus + traffic_penalty + noise


def create_race(drivers, circuit, player_team, grid=None, starting_tyres=None, track_wetness=None, rng=None):
    rng = rng or random
    wetness = _starting_wetness(rng) if track_wetness is None else track_wetness
    weather = _weather_label(wetness)
    states = [_create_driver_state(d, wetness, rng) for d in drivers]
    if grid:
        grid_order = {name: idx for idx, name in enumerate(grid)}
        states.sort(key=lambda s: grid_order.get(s["driver"].name, len(grid)))
        for i, state in enumerate(states, 1):
            state["position"] = i
            state["starting_position"] = i
            if wetness <= DRY_WETNESS:
                # Front of the grid usually starts on softs (with the odd
                # strategic deviation); the rest pick from medium/hard. Wet
                # weekends keep the compound from `initial_tyre` (wet / inter).
                tyre = rng.choice(DRY_FRONT_START) if i <= 8 else rng.choice(DRY_START_FIELD)
                state["tyre"] = tyre
                state["compounds_used"] = [tyre]
    else:
        for state in states:
            state["starting_position"] = None
    if starting_tyres:
        for state in states:
            raw = starting_tyres.get(state["driver"].name)
            if raw:
                tyre = normalize_tyre(raw)
                state["tyre"] = tyre
                state["compounds_used"] = [tyre]
    return {
        "circuit": circuit,
        "player_team": player_team,
        "lap": 0,
        "track_wetness": wetness,
        "weather": weather,
        "rain_state": initial_rain_state(wetness),
        "wet_race_declared": wetness > DRY_WETNESS,
        "states": states,
        "safety_car": False,
        "safety_car_timer": 0,
        "safety_car_laps": 0,
        "red_flag_stoppage": False,
        "weather_grace_laps": 0,
        "team_personas": _build_team_personas(drivers, player_team, rng),
        "rng": rng,
    }


def _build_team_personas(drivers, player_team, rng=None):
    rng = rng or random
    personas = {}
    for d in drivers:
        team = d.team
        if team.id == player_team.id or team.id in personas:
            continue
        personas[team.id] = {
            "risk_tolerance": rng.uniform(PERSONA_RISK_MIN, PERSONA_RISK_MAX),
            "hesitation": rng.uniform(PERSONA_HESITATION_MIN, PERSONA_HESITATION_MAX),
            "stint_bias": rng.uniform(-1.0, 1.0),
        }
    return personas


def run_lap(race_state, player_commands):
    if race_state["red_flag_stoppage"]:
        return _run_red_flag_stoppage_lap(race_state, player_commands)
    rng = race_state.get("rng", random)
    race_state["lap"] += 1
    events = []
    previous_positions = {s["driver"].name: s.get("position", 0) for s in race_state["states"]}
    if race_state["safety_car"]:
        race_state["safety_car_laps"] = race_state.get("safety_car_laps", 0) + 1
    for state in race_state["states"]:
        state["_pitted_this_lap"] = False
        state["_overtook"] = False
        state["_overtaken"] = False
    if race_state.get("weather_grace_laps", 0) > 0:
        race_state["weather_grace_laps"] = 0
        events.append("All cars stay out for a lap as conditions change.")
        # Don't drop the player's tyre choice on the grace lap: hold it and
        # apply it next lap, when the AI also reacts to the new conditions.
        deferred = race_state.get("_deferred_commands", {})
        deferred.update(player_commands or {})
        race_state["_deferred_commands"] = deferred
    else:
        # Apply any tyre command held over from the weather-change lap first,
        # then the fresh commands, then the AI strategy pass.
        deferred = race_state.pop("_deferred_commands", None)
        if deferred:
            _apply_player_commands(race_state, deferred, events)
        _apply_player_commands(race_state, player_commands, events)
        _apply_ai_strategy(race_state, events, rng)
    _update_weather(race_state, events, rng)
    running_before = sorted(
        [s for s in race_state["states"] if s["status"] == "Running"],
        key=lambda s: (s["position"] if s["position"] else 999, s["total_time"]),
    )
    if not any(state["position"] for state in running_before):
        running_before = sorted(running_before, key=lambda s: s["total_time"])
    pre_lap_times = {s["driver"].name: s["total_time"] for s in race_state["states"] if s["status"] == "Running"}
    lap_data = []
    dnf_this_lap = []
    for state in race_state["states"]:
        if state["status"] != "Running":
            continue
        if state["pit_pending"]:
            _do_pit_stop(state, events)
        # A driver pitting on the opening lap avoids the standing-start penalty.
        start_penalty = 0.0
        if race_state["lap"] == 1 and not state.get("_pitted_this_lap") and not state["pit_pending"]:
            start_penalty = _first_lap_grid_penalty(race_state, state, rng)
        lap_time, dnf_reason = _simulate_driver_lap(
            state,
            race_state["circuit"],
            race_state["track_wetness"],
            race_state["safety_car"],
            start_penalty=start_penalty,
            rng=rng,
        )
        if dnf_reason:
            state["status"] = dnf_reason
            state["last_lap"] = None
            state["gap"] = None
            state["interval"] = None
            events.append(f"{state['driver'].name} retired: {dnf_reason}")
            dnf_this_lap.append(dnf_reason)
            continue
        lap_data.append({"state": state, "lap_time": lap_time, "projected_total": state["total_time"] + lap_time})
        state["tyre_age"] += 1
        state["warmup_penalty"] = max(0.0, (state.get("warmup_penalty", 0.0) or 0.0) * TYRE_WARMUP_DECAY - TYRE_WARMUP_FLAT_DROP)
        state["pit_pending"] = None
    _resolve_on_track_order(running_before, lap_data, events, lap_one=(race_state["lap"] == 1), safety_car=race_state["safety_car"], rng=rng)
    red_flag_triggered = _maybe_trigger_red_flag(race_state, dnf_this_lap, pre_lap_times, events, rng)
    if not red_flag_triggered:
        _maybe_deploy_safety_car(race_state, dnf_this_lap, events, rng)
    finished = [s for s in race_state["states"] if s["status"] == "Running"]
    finished.sort(key=lambda s: s["total_time"])
    # The Safety Car slows everyone equally (SAFETY_CAR_LAP_DELTA). On the first
    # lap under SC the existing gaps are kept so a driver can pit before the field
    # bunches; from the second SC lap onward the field is compressed together.
    # Pit costs already paid remain in each driver's time, but stops taken under
    # the SC only count at a fraction of their usual cost.
    if race_state["red_flag_stoppage"] or (
        race_state["safety_car"] and race_state.get("safety_car_laps", 0) >= 2
    ):
        _compress_gaps_under_safety_car(finished)
    dnf_occurred = bool(dnf_this_lap)
    for pos, state in enumerate(finished, 1):
        state["position"] = pos
        state["gap"] = 0.0 if pos == 1 else state["total_time"] - finished[0]["total_time"]
        state["interval"] = 0.0 if pos == 1 else state["total_time"] - finished[pos - 2]["total_time"]
        state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name, 0), pos)
        state["position_delta_reason"] = _describe_position_change(state, state["position_delta"], dnf_occurred)
    retired = [s for s in race_state["states"] if s["status"] != "Running"]
    retired.sort(key=lambda s: s["laps_completed"], reverse=True)
    for idx, state in enumerate(retired, len(finished) + 1):
        state["position"] = idx
        state["gap"] = None
        state["interval"] = None
        state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name, 0), idx)
        state["position_delta_reason"] = f"Retired: {state['status']}"
    _update_safety_car_timer(race_state, events)
    _annotate_risk_levels(race_state)
    return _snapshot(race_state, events)


def is_race_finished(race_state):
    if race_state["lap"] >= race_state["circuit"].laps:
        return True
    return not any(s["status"] == "Running" for s in race_state["states"])


def final_classification(race_state):
    """Pure: returns a final classification without mutating the live race state."""
    states = [dict(s) for s in race_state["states"]]
    is_dry_race = not race_state.get("wet_race_declared", False)
    for state in states:
        if state["status"] == "Running" and is_dry_race:
            dry_used = set(state.get("compounds_used", [])) & set(DRY_START)
            if len(dry_used) < 2:
                state["status"] = "DSQ (Tyre Rule)"
    ordered = sorted(
        states,
        key=lambda s: (
            s["status"] != "Running",
            s["status"] == "DSQ (Tyre Rule)",
            -s["laps_completed"],
            s["total_time"] if s["total_time"] else 10**9,
        ),
    )
    for pos, s in enumerate(ordered, 1):
        s["position"] = pos
    return ordered


def _create_driver_state(driver, track_wetness, rng=None):
    rng = rng or random
    init_tyre = initial_tyre(track_wetness, rng)
    return {
        "driver": driver,
        "total_time": 0.0,
        "last_lap": None,
        "best_lap": None,
        "tyre": init_tyre,
        "tyre_age": 0,
        "warmup_penalty": 0.0,
        "compounds_used": [init_tyre],
        "status": "Running",
        "laps_completed": 0,
        "position": 0,
        "gap": None,
        "interval": None,
        "pit_pending": None,
        "pit_stops": 0,
        "position_delta": 0,
        "position_delta_reason": "Unchanged",
        "risk_level": "Low",
        "laps_in_traffic": 0,
        "total_pit_cost": 0.0,
        "sc_pit_cost": 0.0,
        "pace_luck": rng.gauss(0, LAP_LUCK_SPREAD),
        "_pitted_this_lap": False,
        "_overtook": False,
        "_overtaken": False,
    }


def _position_delta(previous_position, current_position):
    if not previous_position or not current_position:
        return 0
    return previous_position - current_position


def _describe_position_change(state, delta, dnf_occurred=False):
    if delta > 0:
        if state.get("_overtook"):
            return "Overtook on track"
        elif state.get("_pitted_this_lap"):
            return "Gained position despite pit stop"
        elif dnf_occurred:
            return "Gained position (retirement ahead)"
        else:
            return f"Gained {delta} position{'s' if delta > 1 else ''}"
    elif delta < 0:
        if state.get("_pitted_this_lap"):
            return "Lost position during pit stop"
        elif state.get("_overtaken"):
            return "Overtaken on track"
        else:
            return f"Lost {abs(delta)} position{'s' if abs(delta) > 1 else ''}"
    else:
        if state.get("_pitted_this_lap"):
            return "Maintained position after pit stop"
        return "Maintained position"


def _annotate_risk_levels(race_state):
    circuit_laps = race_state["circuit"].laps
    wetness = race_state["track_wetness"]
    for state in race_state["states"]:
        if state["status"] != "Running":
            state["risk_level"] = "N/A"
            continue
        driver = state["driver"]
        tyre_name = normalize_tyre(state["tyre"])
        tyre_info = TYRE_RULES.get(tyre_name, TYRE_RULES["medium"])
        wear_multiplier = SAFETY_CAR_WEAR_MULTIPLIER if race_state["safety_car"] else 1.0
        degradation = _tyre_degradation(state["tyre_age"], tyre_info["deg"], tyre_info["wear_limit"], wear_multiplier)
        wet_penalty = _wet_penalty(wetness, tyre_name)
        rel = getattr(driver.team, "reliability", 50)
        tal = getattr(driver, "talent", 80)
        mech, acc, aqua = _dnf_lap_risks(
            rel,
            tal,
            circuit_laps,
            wetness,
            degradation,
            wet_penalty,
            tyre_name,
            tyre_info["dnf"],
            laps_elapsed=state["laps_completed"],
        )
        # Risk levels compare each driver's race-level DNF chance, not the
        # per-lap probability, so Medium/High actually appear.
        total_risk = (mech + acc + aqua) * circuit_laps
        if total_risk <= RISK_LOW_THRESHOLD:
            state["risk_level"] = "Low"
        elif total_risk <= RISK_MEDIUM_THRESHOLD:
            state["risk_level"] = "Medium"
        else:
            state["risk_level"] = "High"


def _starting_wetness(rng=None):
    rng = rng or random
    roll = rng.randint(1, 100)
    if roll <= 90:
        return 0
    if roll <= 97:
        return rng.randint(6, 30)
    return rng.randint(31, 100)


def _weather_label(wetness):
    if wetness <= DRY_WETNESS:
        return "Dry"
    if wetness <= WET_WETNESS:
        return "Humid"
    if wetness < 70:
        return "Light rain"
    return "Heavy rain"


def _apply_player_commands(race_state, player_commands, events):
    for state in race_state["states"]:
        if state["driver"].team.id != race_state["player_team"].id or state["status"] != "Running":
            continue
        new_tyre_raw = player_commands.get(state["driver"].name)
        if new_tyre_raw:
            new_tyre = normalize_tyre(new_tyre_raw)
            if new_tyre not in VALID_TYRES:
                events.append(f"{state['driver'].name} tyre command '{new_tyre_raw}' ignored: unknown compound.")
                continue
            state["pit_pending"] = new_tyre
            events.append(f"{state['driver'].name} is pitting for {tyre_label(new_tyre)}.")


def _apply_ai_strategy(race_state, events, rng=None):
    rng = rng or random
    laps_remaining = max(0, race_state["circuit"].laps - race_state["lap"])
    safety_car = race_state["safety_car"]
    personas = race_state["team_personas"]
    running_sorted = sorted([s for s in race_state["states"] if s["status"] == "Running"], key=lambda s: s["total_time"])
    position_index = {s["driver"].name: i for i, s in enumerate(running_sorted)}
    is_dry_race = not race_state.get("wet_race_declared", False)
    pit_loss = getattr(race_state["circuit"], "pit_loss", NORMAL_PIT_LOSS)
    sc_pit_loss = SC_PIT_LOSS

    # Iterate from the back of the field so a car's pit intent is known when the
    # car ahead of it evaluates the tactical "cover" reaction.
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
            events.append(f"{state['driver'].name} pits for {tyre_label(state['pit_pending'])} in changing conditions.")
            continue

        if needs_mandatory_compound:
            unused = [t for t in DRY_START if t not in dry_used]
            state["pit_pending"] = unused[0] if unused else _best_tyre_for_conditions(race_state["track_wetness"])
            events.append(f"{state['driver'].name} pits to meet the 2-compound mandatory tyre rule.")
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


def _tyre_degradation(age, deg, wear_limit, wear_multiplier=1.0):
    """Progressive tyre degradation.

    Low in the first laps (green phase), rising smoothly to the cliff at the wear
    limit, then falling off sharply if the driver overextends the stint.
    """
    wl = max(1.0, wear_limit)
    if age <= wl:
        p = age / wl
        return (DEG_GREEN_1 * p + DEG_GREEN_2 * p * p + DEG_GREEN_4 * p * p * p * p) * deg * wear_multiplier
    over = age - wl
    return (DEG_PAST_BASE + DEG_PAST_SLOPE * over) * deg * wear_multiplier


def _stint_time_loss(age, deg, wear_limit, laps, wear_multiplier=1.0):
    """Total seconds lost to degradation over the next `laps` laps from `age`."""
    total = 0.0
    for _ in range(max(0, int(laps))):
        total += _tyre_degradation(age, deg, wear_limit, wear_multiplier)
        age += 1
    return total


def _update_weather(race_state, events, rng=None):
    rng = rng or random
    _evolve_rain_state(race_state, events, rng)
    change = _wetness_delta(race_state["rain_state"], race_state["track_wetness"], rng)
    race_state["track_wetness"] = max(0, min(100, race_state["track_wetness"] + change))
    if race_state["track_wetness"] > DRY_WETNESS:
        race_state["wet_race_declared"] = True
    new_weather = _weather_label(race_state["track_wetness"])
    if new_weather != race_state["weather"]:
        race_state["weather"] = new_weather
        race_state["weather_grace_laps"] = 1
        events.append(f"Weather changed to {new_weather} ({race_state['track_wetness']}% wet).")


def _do_pit_stop(state, events):
    new_tyre = normalize_tyre(state["pit_pending"])
    state["tyre"] = new_tyre
    state["tyre_age"] = 0
    state["warmup_penalty"] = TYRE_WARMUP_PENALTY
    state["pit_stops"] += 1
    state["_pitted_this_lap"] = True
    if "compounds_used" not in state:
        state["compounds_used"] = []
    if new_tyre not in state["compounds_used"]:
        state["compounds_used"].append(new_tyre)
    events.append(f"{state['driver'].name} switched to {tyre_label(new_tyre)} tyres.")


def _simulate_driver_lap(state, circuit, track_wetness, safety_car=False, start_penalty=0.0, rng=None):
    rng = rng or random
    tyre_key = normalize_tyre(state["tyre"])
    tyre = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
    driver = state["driver"]
    reliability = getattr(driver.team, "reliability", 50)

    driver_gain, car_gain = _pace_terms(driver, circuit)
    wear_multiplier = SAFETY_CAR_WEAR_MULTIPLIER if safety_car else 1.0

    # Increased thermal degradation if running wet tyres on a dry track
    if track_wetness <= DRY_WETNESS and tyre_key in ("intermediate", "wet"):
        wear_multiplier *= WET_ON_DRY_WEAR_MULTIPLIER

    degradation = _tyre_degradation(state["tyre_age"], tyre["deg"], tyre["wear_limit"], wear_multiplier)
    global_wet_slowdown = track_wetness * WET_SLOWDOWN_PER_WETNESS
    wet_penalty = _wet_penalty(track_wetness, tyre_key)
    noise = rng.gauss(0, LAP_NOISE) + state.get("pace_luck", 0.0)
    pit_loss = getattr(circuit, "pit_loss", NORMAL_PIT_LOSS) if (state.get("pit_pending") or state.get("_pitted_this_lap")) else 0.0
    if pit_loss:
        # A stop taken under the Safety Car only costs the flat SC_PIT_LOSS
        # (the field is already bunched) versus the full green-flag pit_loss.
        if safety_car:
            pit_loss = SC_PIT_LOSS
        state["total_pit_cost"] = state.get("total_pit_cost", 0.0) + pit_loss
        if safety_car:
            state["sc_pit_cost"] = state.get("sc_pit_cost", 0.0) + pit_loss
    warmup = state.get("warmup_penalty", 0.0) or 0.0
    safety_car_delta = SAFETY_CAR_LAP_DELTA if safety_car else 0.0
    traffic_penalty = min(state.get("laps_in_traffic", 0), TRAFFIC_PENALTY_CAP_LAPS) * TRAFFIC_PENALTY_PER_LAP
    lap_time = (
        circuit.base_lap_time
        - driver_gain
        - car_gain
        + tyre["pace"]
        + degradation
        + global_wet_slowdown
        + wet_penalty
        + pit_loss
        + warmup
        + safety_car_delta
        + traffic_penalty
        + noise
        + start_penalty
    )
    dnf_reason = _lap_dnf_event(
        reliability,
        getattr(driver, "talent", 80),
        circuit.laps,
        track_wetness,
        degradation,
        wet_penalty,
        tyre_key,
        tyre["dnf"],
        laps_elapsed=state["laps_completed"],
        rng=rng,
    )
    if dnf_reason:
        return None, dnf_reason
    return lap_time, None


def _first_lap_grid_penalty(race_state, state, rng=None):
    """Extra time lost on lap 1 based on grid slot (standing start, dirty air, traffic)."""
    rng = rng or random
    pos = state.get("starting_position") or state.get("position") or 1
    if pos <= 1:
        lo, hi = 1.0, 1.5
    elif pos <= 5:
        lo, hi = 1.5, 2.2
    elif pos <= 10:
        lo, hi = 2.0, 3.0
    elif pos <= 15:
        lo, hi = 3.0, 4.5
    else:
        lo, hi = 4.5, 6.5
    penalty = rng.uniform(lo, hi)
    # A fast driver trapped behind a notably slower car ahead loses extra time
    ahead = _driver_ahead_in_grid(race_state, state)
    if ahead is not None and ahead["status"] == "Running":
        circuit = race_state["circuit"]
        my_pace = projected_pace(state["driver"], circuit, "soft")
        ahead_pace = projected_pace(ahead["driver"], circuit, "soft")
        if my_pace < ahead_pace - 0.5:
            penalty += rng.uniform(0.4, 1.3)
    return penalty


def _driver_ahead_in_grid(race_state, state):
    pos = state.get("starting_position") or state.get("position") or 1
    if pos <= 1:
        return None
    target = pos - 1
    for s in race_state["states"]:
        if (s.get("starting_position") or s.get("position")) == target:
            return s
    return None


def _wet_penalty(track_wetness, tyre_name):
    tyre_key = normalize_tyre(tyre_name)
    tyre = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
    if tyre["wet_low"] <= track_wetness <= tyre["wet_high"]:
        return 0.0
    if track_wetness < tyre["wet_low"]:
        return (tyre["wet_low"] - track_wetness) * 0.05
    return (track_wetness - tyre["wet_high"]) * 0.08


def _snapshot(race_state, events):
    ordered = sorted(race_state["states"], key=lambda s: s["position"])
    return {
        "lap": race_state["lap"],
        "laps": race_state["circuit"].laps,
        "weather": race_state["weather"],
        "track_wetness": race_state["track_wetness"],
        "safety_car": race_state["safety_car"],
        "red_flag_stoppage": race_state["red_flag_stoppage"],
        "rain_state": race_state["rain_state"],
        "table": ordered,
        "events": events,
    }


def initial_rain_state(wetness):
    if wetness > WET_WETNESS:
        return "heavy"
    if wetness > DRY_WETNESS:
        return "light"
    return "dry"


def _evolve_rain_state(race_state, events, rng=None):
    rng = rng or random
    rain_multiplier = max(0.1, getattr(race_state["circuit"], "rain_chance_multiplier", 1.0))
    previous = race_state["rain_state"]
    new_state = _rain_transition(previous, rain_multiplier, rng.random())
    if new_state == previous:
        return
    race_state["rain_state"] = new_state
    if previous == "dry":
        events.append("It has started drizzling.")
    elif new_state == "dry":
        events.append("The rain has stopped.")
    elif new_state == "heavy":
        events.append("The rain has intensified.")
    else:
        events.append("The rain has eased.")


def _rain_transition(rain_state, rain_multiplier, roll):
    """Next rain state after one lap given a roll in [0, 1).

    Single source of truth for the rain model, shared by the race simulation
    and the Monte-Carlo weather forecast.
    """
    if rain_state == "dry":
        if roll < min(RAIN_MAX_PROB, RAIN_DRY_TO_LIGHT * rain_multiplier):
            return "light"
        return "dry"
    if rain_state == "light":
        stop_threshold = min(RAIN_MAX_PROB, RAIN_LIGHT_TO_DRY / rain_multiplier)
        intensify_threshold = stop_threshold + min(RAIN_MAX_PROB, RAIN_LIGHT_TO_HEAVY * rain_multiplier)
        if roll < stop_threshold:
            return "dry"
        if roll < intensify_threshold:
            return "heavy"
        return "light"
    if roll < min(RAIN_MAX_PROB, RAIN_HEAVY_TO_LIGHT / rain_multiplier):
        return "light"
    return "heavy"


def _wetness_delta(rain_state, track_wetness, rng=None):
    rng = rng or random
    if rain_state == "dry":
        if track_wetness == 0:
            return 0
        return -rng.randint(2, 6)
    if rain_state == "light":
        if track_wetness < DRY_WETNESS:
            return rng.randint(1, 3)
        return rng.randint(-1, 3)
    return rng.randint(3, 8)


def weather_forecast(circuit, rain_state, track_wetness, horizons=(5, 10, 20), trials=2000):
    """Monte-Carlo estimate of the chance of rain (track wetness > 5) within the
    next `horizons` laps, using the same rain model as the race simulation.

    Uses a dedicated RNG so querying the forecast never disturbs the race.
    """
    rng = _FORECAST_RNG
    mult = max(0.1, getattr(circuit, "rain_chance_multiplier", 1.0))
    max_lap = max(horizons)
    counts = {h: 0 for h in horizons}
    for _ in range(trials):
        rs = rain_state
        w = track_wetness
        hit_lap = None
        for lap in range(1, max_lap + 1):
            rs = _rain_transition(rs, mult, rng.random())
            w = max(0, min(100, w + _wetness_delta(rs, w, rng)))
            if w > DRY_WETNESS:
                hit_lap = lap
                break
        if hit_lap is None:
            continue
        for h in horizons:
            if hit_lap <= h:
                counts[h] += 1
    return {str(h): int(round(counts[h] / trials * 100)) for h in horizons}


def _dnf_lap_risks(reliability, talent, laps, track_wetness, degradation, wet_penalty, tyre_name, tyre_risk, laps_elapsed=0):
    mechanical = _race_to_lap_risk(MECH_BASE + (100 - reliability) * MECH_RELIABILITY_FACTOR, max(1, laps)) * (1.0 + 0.5 * (laps_elapsed / max(1, laps)))
    accident_base = ACCIDENT_BASE + max(0.0, degradation - 1.2) * ACCIDENT_DEG_FACTOR + max(0.0, wet_penalty - 0.6) * ACCIDENT_WET_FACTOR + tyre_risk * TYRE_DNF_WEIGHT
    accident_skill = max(ACCIDENT_SKILL_FLOOR, ACCIDENT_SKILL_BASE - (talent - 80) * ACCIDENT_SKILL_TALENT)
    accident = _race_to_lap_risk(min(ACCIDENT_MAX, accident_base * accident_skill), max(1, laps))
    aquaplane = _race_to_lap_risk(_aquaplane_race_risk(track_wetness, wet_penalty, tyre_name), max(1, laps))
    return mechanical, accident, aquaplane


def _lap_dnf_event(reliability, talent, laps, track_wetness, degradation, wet_penalty, tyre_name, tyre_risk, laps_elapsed=0, rng=None):
    rng = rng or random
    mechanical, accident, aquaplane = _dnf_lap_risks(
        reliability,
        talent,
        laps,
        track_wetness,
        degradation,
        wet_penalty,
        tyre_name,
        tyre_risk,
        laps_elapsed=laps_elapsed,
    )
    roll = rng.random()
    if roll < mechanical:
        return "Mechanical failure"
    if roll < mechanical + accident:
        return "Accident"
    if roll < mechanical + accident + aquaplane:
        return "Aquaplaning"
    return None


def _race_to_lap_risk(race_risk, laps):
    return max(0.0, min(0.95, race_risk)) / laps


def _aquaplane_race_risk(track_wetness, wet_penalty, tyre_name):
    tyre_key = normalize_tyre(tyre_name)
    if tyre_key in DRY_START:
        if track_wetness <= WET_WETNESS:
            return 0.0
        return min(0.16, (track_wetness - WET_WETNESS) * 0.002 + wet_penalty * 0.025)
    if tyre_key == "intermediate":
        if track_wetness >= 65:
            return min(0.07, (track_wetness - 65) * 0.0015 + wet_penalty * 0.012)
        # Damp crossover band: intermediates can still catch standing water.
        if track_wetness > DRY_WETNESS:
            return min(0.02, (track_wetness - DRY_WETNESS) * 0.0006 + wet_penalty * 0.003)
        return 0.0
    return 0.0


def _resolve_on_track_order(running_before, lap_data, events, lap_one=False, safety_car=False, rng=None):
    rng = rng or random
    data_by_id = {entry["state"]["driver"].name: entry for entry in lap_data}
    ordered = []
    for state in running_before:
        if state["status"] != "Running":
            continue
        entry = data_by_id.get(state["driver"].name)
        if entry:
            ordered.append(entry)
    for entry in lap_data:
        if entry not in ordered:
            ordered.append(entry)
    if not ordered:
        return
    resolved = [ordered[0]]
    for entry in ordered[1:]:
        front = resolved[-1]
        front_state = front["state"]
        state = entry["state"]
        start_gap = max(0.0, state["total_time"] - front_state["total_time"])
        if front_state.get("_pitted_this_lap"):
            resolved[-1], entry = entry, front
            state["laps_in_traffic"] = 0
            front_state["laps_in_traffic"] = 0
        elif not safety_car and entry["projected_total"] < front["projected_total"] and start_gap < PASS_WINDOW:
            laps_stuck = state.get("laps_in_traffic", 0)
            talent = getattr(state["driver"], "talent", 80)
            pace_advantage = front["projected_total"] - entry["projected_total"]
            if pace_advantage > OVERTAKE_MIN_PACE and _overtake_succeeds(talent, start_gap, laps_stuck, lap_one, rng, pace_advantage):
                resolved[-1], entry = entry, front
                events.append(f"{state['driver'].name} passed {front_state['driver'].name}.")
                state["_overtook"] = True
                front_state["_overtaken"] = True
                state["laps_in_traffic"] = 0
                front_state["laps_in_traffic"] = 0
            else:
                # Stuck in dirty air: lap-time penalty applies on its own, without
                # also clamping the car to the leader (which double-penalised it).
                state["laps_in_traffic"] = laps_stuck + 1
                if state["laps_in_traffic"] in (3, 6, 9):
                    events.append(f"{state['driver'].name} is stuck in traffic behind {front_state['driver'].name}.")
        else:
            state["laps_in_traffic"] = 0
        resolved.append(entry)
    for entry in resolved:
        state = entry["state"]
        state["total_time"] = entry["projected_total"]
        state["last_lap"] = entry["lap_time"]
        if entry["lap_time"] is not None:
            if state.get("best_lap") is None or entry["lap_time"] < state["best_lap"]:
                state["best_lap"] = entry["lap_time"]
        state["laps_completed"] = state["laps_completed"] + 1


def _overtake_succeeds(talent, start_gap, laps_in_traffic=0, lap_one=False, rng=None, pace_advantage=0.0):
    rng = rng or random
    traffic_bonus = min(laps_in_traffic, TRAFFIC_OVERTAKE_BONUS_CAP_LAPS) * TRAFFIC_OVERTAKE_BONUS_PER_LAP
    chance = (
        OVERTAKE_BASE_CHANCE
        + max(0, talent - 80) * OVERTAKE_TALENT_FACTOR
        + (1.0 - start_gap) * OVERTAKE_GAP_FACTOR
        + traffic_bonus
        + pace_advantage * OVERTAKE_PACE_FACTOR
    )
    if lap_one:
        chance += OVERTAKE_LAP_ONE_BONUS
    return rng.random() < min(OVERTAKE_MAX_CHANCE, max(OVERTAKE_MIN_CHANCE, chance))


def _best_tyre_for_conditions(track_wetness):
    if track_wetness > WET_WETNESS:
        return "wet"
    if track_wetness > DRY_WETNESS:
        return "intermediate"
    if track_wetness <= 2:
        return "soft"
    if track_wetness <= 4:
        return "medium"
    return "hard"


def _deploy_safety_car(race_state, events, rng=None):
    rng = rng or random
    race_state["safety_car"] = True
    race_state["safety_car_timer"] = rng.randint(SC_MIN_TIMER, SC_MAX_TIMER)
    race_state["safety_car_laps"] = 0
    events.append("Safety Car deployed.")


def _maybe_deploy_safety_car(race_state, dnf_reasons, events, rng=None):
    rng = rng or random
    if race_state["safety_car"]:
        return
    if "Accident" in dnf_reasons:
        chance = SC_ACCIDENT_CHANCE
    elif "Aquaplaning" in dnf_reasons:
        chance = SC_AQUAPLANE_CHANCE
    elif "Mechanical failure" in dnf_reasons:
        chance = SC_MECHANICAL_CHANCE
    else:
        return
    if rng.random() < chance:
        _deploy_safety_car(race_state, events, rng)


def _update_safety_car_timer(race_state, events):
    if not race_state["safety_car"]:
        return
    race_state["safety_car_timer"] -= 1
    if race_state["safety_car_timer"] <= 0:
        race_state["safety_car"] = False
        race_state["safety_car_timer"] = 0
        events.append("Safety Car in. Green Flag.")


def _compress_gaps_under_safety_car(finished):
    """Bunch the running field into a tight train under the Safety Car.

    Each car is pulled forward to the train position `base + idx * SAFETY_CAR_GAP_STEP`
    but never pushed further back than it already was. This compresses the field
    without erasing a car's hard-earned on-track time, and without double-counting
    pit-stop costs (pit losses are already reflected in each car's total_time and
    in its position within the sorted field).
    """
    if not finished:
        return
    base = finished[0]["total_time"]
    for idx, state in enumerate(finished):
        train_time = base + idx * SAFETY_CAR_GAP_STEP
        if state["total_time"] > train_time:
            state["total_time"] = train_time


def _maybe_trigger_red_flag(race_state, dnf_reasons, pre_lap_times, events, rng=None):
    rng = rng or random
    if race_state["red_flag_stoppage"]:
        return False
    accidents = dnf_reasons.count("Accident")
    if accidents >= RED_FLAG_ACCIDENTS:
        triggered = True
    elif accidents == 1:
        triggered = rng.random() < RED_FLAG_SINGLE_CHANCE
    else:
        triggered = False
    if not triggered:
        return False
    race_state["red_flag_stoppage"] = True
    race_state["safety_car"] = False
    race_state["safety_car_timer"] = 0
    events.append("Red Flag: race suspended following a serious incident.")
    for state in race_state["states"]:
        if state["status"] != "Running":
            continue
        prev_total = pre_lap_times.get(state["driver"].name)
        if prev_total is not None:
            state["total_time"] = prev_total
        state["last_lap"] = None
        state["laps_in_traffic"] = 0
        if state["laps_completed"] > 0:
            state["laps_completed"] -= 1
    return True


def _run_red_flag_stoppage_lap(race_state, player_commands):
    rng = race_state.get("rng", random)
    events = []
    race_state["lap"] += 1
    previous_positions = {s["driver"].name: s.get("position", 0) for s in race_state["states"]}
    _apply_player_commands(race_state, player_commands, events)
    for state in race_state["states"]:
        if state["driver"].team.id == race_state["player_team"].id or state["status"] != "Running" or state["pit_pending"]:
            continue
        suggested = _best_tyre_for_conditions(race_state["track_wetness"])
        if suggested != normalize_tyre(state["tyre"]):
            state["pit_pending"] = suggested
    for state in race_state["states"]:
        if state["status"] == "Running" and state["pit_pending"]:
            _do_pit_stop(state, events)
            state["pit_pending"] = None
            state["last_lap"] = None
    finished = [s for s in race_state["states"] if s["status"] == "Running"]
    finished.sort(key=lambda s: s["total_time"])
    _compress_gaps_under_safety_car(finished)
    for state in finished:
        state["laps_completed"] += 1
    for pos, state in enumerate(finished, 1):
        state["position"] = pos
        state["gap"] = 0.0 if pos == 1 else state["total_time"] - finished[0]["total_time"]
        state["interval"] = 0.0 if pos == 1 else state["total_time"] - finished[pos - 2]["total_time"]
        state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name, 0), pos)
        state["position_delta_reason"] = _describe_position_change(state, state["position_delta"])
    retired = [s for s in race_state["states"] if s["status"] != "Running"]
    retired.sort(key=lambda s: s["laps_completed"], reverse=True)
    for idx, state in enumerate(retired, len(finished) + 1):
        state["position"] = idx
        state["gap"] = None
        state["interval"] = None
        state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name, 0), idx)
        state["position_delta_reason"] = f"Retired: {state['status']}"
    race_state["red_flag_stoppage"] = False
    race_state["safety_car"] = True
    race_state["safety_car_timer"] = rng.randint(SC_AFTER_RED_FLAG_MIN, SC_AFTER_RED_FLAG_MAX)
    events.append("Race resumes behind the Safety Car.")
    return _snapshot(race_state, events)
