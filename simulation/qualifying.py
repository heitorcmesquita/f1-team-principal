import heapq
import random

from simulation.race import (
    projected_pace,
    qualifying_lap_time,
    _starting_wetness,
    _weather_label,
)

# One Q session = 10 simulated minutes of track time.
SESSION_DURATION = 600
PHASES = ("Q1", "Q2", "Q3")
# Bottom 6 drivers are eliminated at the end of Q1 and Q2.
ELIMINATED_PER_PHASE = {"Q1": 6, "Q2": 6, "Q3": 0}
MAX_RUNS_PER_DRIVER = 2


def create_qualifying(drivers, circuit, track_wetness=None):
    """Start a fresh qualifying weekend for the given drivers.

    The track weather is rolled here so the race (which reuses the weekend
    weather) stays consistent with what the drivers experienced in qualifying.
    """
    wetness = _starting_wetness() if track_wetness is None else track_wetness
    weather = _weather_label(wetness)
    qual = {
        "circuit": circuit,
        "track_wetness": wetness,
        "weather": weather,
        "phase": "Q1",
        "phase_index": 0,
        "session_duration": SESSION_DURATION,
        "elapsed": 0.0,
        "time_left": SESSION_DURATION,
        "global_elapsed": 0.0,
        "phase_base": 0.0,
        "entries": {d.name: _new_entry(d) for d in drivers},
        "active_names": [d.name for d in drivers],
        "runs": [],
        "run2": {},
        "timeline": [],
        "_seq": 0,
        "events": [],
        "fastest_lap": None,
        "eliminated": [],
        "grid": [],
        "phase_finished": False,
        "finished": False,
    }
    _prepare_phase(qual)
    return qual


def advance_qualifying(qual, seconds):
    """Advance the current Q session by `seconds` of simulated track time.

    Returns (qual, events). When the session runs out of time the phase is
    finalized (eliminations or final grid) and the next phase is prepared
    automatically.
    """
    events = []
    if qual["finished"]:
        return qual, events
    target = min(qual["session_duration"], qual["elapsed"] + max(0.0, seconds))
    while qual["timeline"] and qual["timeline"][0][0] <= target:
        t, _seq, kind, payload = heapq.heappop(qual["timeline"])
        if kind == "out2":
            _process_run2(qual, payload, events)
        elif kind == "out":
            name, run = payload
            qual["entries"][name]["on_track"] = True
        elif kind == "fly":
            name, run = payload
            if not run["done"] and name in qual["active_names"]:
                _execute_flying_lap(qual, run, t, events)
        elif kind == "in":
            name, run = payload
            qual["entries"][name]["on_track"] = False
    qual["elapsed"] = target
    qual["time_left"] = qual["session_duration"] - target
    qual["global_elapsed"] = qual["phase_base"] + target
    if qual["time_left"] <= 0:
        _finish_phase(qual, events)
    return qual, events


def skip_qualifying(qual, target_phase=None):
    """Fast-forward through the rest of the current session (and any following
    sessions) until the requested phase starts, or until the full starting grid
    is complete when no target is given."""
    events = []
    guard = 0
    if target_phase and target_phase in PHASES:
        target_index = PHASES.index(target_phase)
        while not qual["finished"] and PHASES.index(qual["phase"]) < target_index and guard < len(PHASES) * 2:
            guard += 1
            _, phase_events = advance_qualifying(qual, qual["time_left"] or qual["session_duration"])
            events.extend(phase_events)
        return qual, events
    while not qual["finished"] and guard < len(PHASES) * 2:
        guard += 1
        _, phase_events = advance_qualifying(qual, qual["time_left"] or qual["session_duration"])
        events.extend(phase_events)
    return qual, events


def qualifying_snapshot(qual):
    """Serializable snapshot of the current qualifying state for the API."""
    rows = []
    if qual["finished"]:
        entries = [e for e in qual["entries"].values() if e["grid_position"] is not None]
        entries.sort(key=lambda e: e["grid_position"])
        rows = [_row(qual, e, e["grid_position"]) for e in entries]
    else:
        order = _classification(qual)
        rows = [_row(qual, qual["entries"][n], i + 1) for i, n in enumerate(order)]
        eliminated = [e for e in qual["entries"].values() if e["eliminated"]]
        eliminated.sort(key=lambda e: e["grid_position"])
        rows.extend([_row(qual, e, e["grid_position"]) for e in eliminated])

    return {
        "phase": qual["phase"],
        "time_left": int(round(qual["time_left"])),
        "session_duration": qual["session_duration"],
        "weather": qual["weather"],
        "track_wetness": qual["track_wetness"],
        "fastest_lap": qual["fastest_lap"],
        "eliminated": list(qual["eliminated"]),
        "phase_finished": qual["phase_finished"],
        "finished": qual["finished"],
        "classification": rows,
        "grid": [
            {
                "position": e["grid_position"],
                "driver": e["driver"].name,
                "team": e["team"],
                "best_lap": e["best_lap"],
                "eliminated": e["eliminated"],
            }
            for e in sorted(qual["entries"].values(), key=lambda x: x["grid_position"] or 999)
        ]
        if qual["finished"]
        else [],
        "events": qual["events"][-40:],
    }


def grid_names(qual):
    """Return the final grid as an ordered list of driver names."""
    entries = [e for e in qual["entries"].values() if e["grid_position"] is not None]
    entries.sort(key=lambda e: e["grid_position"])
    return [e["driver"].name for e in entries]


# --------------------------------------------------------------------------- #
# Scheduling helpers
# --------------------------------------------------------------------------- #
def _new_entry(driver):
    return {
        "driver": driver,
        "team": driver.team.name,
        "best_lap": None,
        "runs_done": 0,
        "on_track": False,
        "phase_bests": {},
        "grid_position": None,
        "eliminated": False,
    }


def _prepare_phase(qual):
    qual["phase_base"] = qual["global_elapsed"]
    qual["elapsed"] = 0.0
    qual["time_left"] = qual["session_duration"]
    qual["runs"] = []
    qual["run2"] = {}
    qual["timeline"] = []
    qual["_seq"] = 0
    qual["phase_finished"] = False
    qual["fastest_lap"] = None
    for name in qual["active_names"]:
        entry = qual["entries"][name]
        entry["best_lap"] = None
        entry["on_track"] = False
    _plan_first_runs(qual)
    _plan_second_runs(qual)


def _push_event(qual, t, kind, payload):
    qual["_seq"] += 1
    heapq.heappush(qual["timeline"], (t, qual["_seq"], kind, payload))


def _session_tyre(qual):
    wet = qual["track_wetness"]
    if wet > 30:
        return "wet"
    return "soft"


def _new_run(qual, name, out_time, second):
    entry = qual["entries"][name]
    driver = entry["driver"]
    circuit = qual["circuit"]
    tyre = _session_tyre(qual)
    pace = projected_pace(driver, circuit, tyre)
    flying_start = out_time + pace + random.uniform(8.0, 16.0)
    flying_end = flying_start + pace + random.uniform(18.0, 28.0)
    run = {
        "driver": name,
        "tyre": tyre,
        "out_time": out_time,
        "flying_start": flying_start,
        "flying_end": flying_end,
        "done": False,
        "lap": None,
        "traffic": False,
        "second": second,
    }
    qual["runs"].append(run)
    _push_event(qual, out_time, "out", (name, run))
    _push_event(qual, flying_start, "fly", (name, run))
    _push_event(qual, flying_end, "in", (name, run))
    return run


def _plan_first_runs(qual):
    """Every driver gets a first run. Slower cars leave the garage first, the
    quickest teams wait longer (top teams like to save tyres and find clean air).
    """
    active = qual["active_names"]
    circuit = qual["circuit"]
    session = qual["session_duration"]
    paced = sorted(active, key=lambda n: projected_pace(qual["entries"][n]["driver"], circuit, "soft"))
    count = len(paced)
    for i, name in enumerate(paced):
        progress = (i / max(1, count)) ** 1.25
        out_time = 25 + progress * session * 0.55 + random.uniform(-12, 12)
        out_time = max(8.0, min(session - 260.0, out_time))
        _new_run(qual, name, out_time, second=False)


def _plan_second_runs(qual):
    """Each driver plans a possible second run late in the session. Whether it
    actually happens is decided when the driver would leave the garage, based
    on the live classification (teams near elimination push harder, safe top
    teams usually skip it)."""
    active = qual["active_names"]
    circuit = qual["circuit"]
    session = qual["session_duration"]
    paced = sorted(active, key=lambda n: projected_pace(qual["entries"][n]["driver"], circuit, "soft"))
    count = len(paced)
    for i, name in enumerate(paced):
        progress = i / max(1, count)
        out_time = session - 150 - (1.0 - progress) * 150 + random.uniform(-15, 15)
        out_time = max(session - 320.0, min(session - 25.0, out_time))
        qual["run2"][name] = {"out_time": out_time, "activated": False}
        _push_event(qual, out_time, "out2", name)


def _process_run2(qual, name, events):
    entry = qual["entries"][name]
    if name not in qual["active_names"]:
        return
    if entry["runs_done"] >= MAX_RUNS_PER_DRIVER:
        return
    circuit = qual["circuit"]
    tyre = _session_tyre(qual)
    pace = projected_pace(entry["driver"], circuit, tyre)
    out_time = qual["run2"][name]["out_time"]
    if out_time + pace + 20.0 > qual["session_duration"]:
        return
    if not _decide_run2(qual, name):
        return
    qual["run2"][name]["activated"] = True
    _new_run(qual, name, out_time, second=True)
    events.append(f"{name} heads out for a second run.")


def _decide_run2(qual, name):
    entry = qual["entries"][name]
    if entry["best_lap"] is None:
        return True
    order = _classification(qual)
    total = len(order)
    pos = order.index(name) if name in order else total
    at_risk = pos >= total * 0.5
    if at_risk:
        return random.random() < 0.9
    circuit = qual["circuit"]
    pace = projected_pace(entry["driver"], circuit, "soft")
    field = [projected_pace(qual["entries"][n]["driver"], circuit, "soft") for n in qual["active_names"] if n != name]
    avg = sum(field) / max(1, len(field))
    chance = 0.45 - max(0.0, (avg - pace)) * 0.35
    return random.random() < max(0.10, min(0.45, chance))


def _execute_flying_lap(qual, run, t, events):
    name = run["driver"]
    entry = qual["entries"][name]
    run["done"] = True
    entry["runs_done"] += 1

    # Qualifying runs always take place in clean air — no traffic penalty.
    traffic = 0.0

    # Track evolution: rubber goes down all weekend, ~0.8-1.2s faster by the end of Q3.
    total_session = qual["session_duration"] * len(PHASES)
    evolution_progress = (qual["phase_base"] + t) / total_session
    evolution = -evolution_progress * random.uniform(0.8, 1.2)
    if qual["track_wetness"] > 5:
        evolution *= 0.5

    lap = qualifying_lap_time(
        entry["driver"],
        qual["circuit"],
        qual["track_wetness"],
        run["tyre"],
        evolution_bonus=evolution,
        traffic_penalty=traffic,
    )
    run["lap"] = lap
    if entry["best_lap"] is None or lap < entry["best_lap"]:
        entry["best_lap"] = lap
        qual["fastest_lap"] = {"driver": name, "team": entry["team"], "lap": lap}
    events.append(f"{name} sets {_fmt_time(lap)}.")


def _classification(qual):
    with_time = []
    no_time = []
    for name in qual["active_names"]:
        best = qual["entries"][name]["best_lap"]
        if best is not None:
            with_time.append((name, best))
        else:
            no_time.append(name)
    with_time.sort(key=lambda x: x[1])
    return [name for name, _ in with_time] + no_time


def _finish_phase(qual, events):
    order = _classification(qual)
    phase = qual["phase"]
    eliminated_count = ELIMINATED_PER_PHASE[phase]
    if eliminated_count:
        already = len(qual["eliminated"])
        eliminated = order[-eliminated_count:]
        grid_start = len(qual["entries"]) - already - len(eliminated) + 1
        for idx, name in enumerate(eliminated):
            entry = qual["entries"][name]
            entry["eliminated"] = True
            entry["grid_position"] = grid_start + idx
            entry["phase_bests"][phase] = entry["best_lap"]
        qual["eliminated"].extend(eliminated)
        events.append(f"{phase} over: {' , '.join(eliminated)} eliminated.")
        qual["active_names"] = [n for n in qual["active_names"] if n not in eliminated]
        qual["phase_index"] += 1
        qual["phase"] = PHASES[qual["phase_index"]]
        _prepare_phase(qual)
    else:
        for idx, name in enumerate(order):
            entry = qual["entries"][name]
            entry["grid_position"] = idx + 1
            entry["phase_bests"]["Q3"] = entry["best_lap"]
        qual["grid"] = grid_names(qual)
        qual["phase_finished"] = True
        qual["finished"] = True
        events.append("Q3 over: the starting grid is set.")


def _row(qual, entry, position):
    return {
        "position": position,
        "driver": entry["driver"].name,
        "team": entry["team"],
        "best_lap": entry["best_lap"],
        "runs_done": entry["runs_done"],
        "on_track": entry["on_track"],
        "eliminated": entry["eliminated"],
        "grid_position": entry["grid_position"],
    }


def _fmt_time(lap):
    minutes = int(lap // 60)
    seconds = lap - minutes * 60
    return f"{minutes}:{seconds:06.3f}"
