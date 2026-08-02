import sys
from pathlib import Path
import pytest

# Ensure root is in sys.path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from utils import load
from simulation.qualifying import (
    create_qualifying,
    advance_qualifying,
    skip_qualifying,
    qualifying_snapshot,
    grid_names,
)
from simulation.race import create_race, projected_pace


def _finished_qualifying():
    drivers, circuits = load()
    qual = create_qualifying(drivers, circuits[0])
    skip_qualifying(qual)
    return qual


def test_create_qualifying():
    drivers, circuits = load()
    qual = create_qualifying(drivers, circuits[0])
    assert qual["phase"] == "Q1"
    assert qual["time_left"] == qual["session_duration"]
    assert set(qual["active_names"]) == {d.name for d in drivers}
    assert not qual["finished"]


def test_skip_produces_full_grid():
    qual = _finished_qualifying()
    grid = grid_names(qual)
    drivers, _ = load()
    assert len(grid) == len(drivers)
    assert len(set(grid)) == len(drivers)


def test_grid_positions_are_sequential():
    qual = _finished_qualifying()
    positions = sorted(e["grid_position"] for e in qual["entries"].values())
    assert positions == list(range(1, len(positions) + 1))


def test_eliminations_reduce_field_each_phase():
    qual = _finished_qualifying()
    # Q3 keeps only the top N-12 drivers (6 eliminated in Q1 + 6 in Q2)
    drivers, _ = load()
    q3_drivers = [n for n, e in qual["entries"].items() if e["phase_bests"].get("Q3")]
    assert len(q3_drivers) == len(drivers) - 12


def test_eliminated_drivers_have_lap_times():
    qual = _finished_qualifying()
    drivers, _ = load()
    eliminated = [e for e in qual["entries"].values() if e["eliminated"]]
    assert len(eliminated) == 12
    for e in eliminated:
        assert e["best_lap"] is not None


def test_snapshot_shape():
    qual = _finished_qualifying()
    snap = qualifying_snapshot(qual)
    assert snap["finished"] is True
    assert snap["grid"]
    assert snap["phase"] == "Q3"
    assert snap["classification"]


def test_race_uses_qualifying_grid():
    drivers, circuits = load()
    player_team = drivers[0].team
    qual = create_qualifying(drivers, circuits[0])
    skip_qualifying(qual)
    grid = grid_names(qual)
    race = create_race(
        drivers,
        circuits[0],
        player_team,
        grid=grid,
        starting_tyres={grid[0]: "soft"},
        track_wetness=qual["track_wetness"],
    )
    states = sorted(race["states"], key=lambda s: s["position"])
    assert [s["driver"].name for s in states] == grid
    assert states[0]["starting_position"] == 1
    assert states[0]["tyre"] == "soft"


def test_projected_pace_deterministic():
    drivers, circuits = load()
    p1 = projected_pace(drivers[0], circuits[0], "soft")
    p2 = projected_pace(drivers[0], circuits[0], "soft")
    assert p1 == p2


def test_advance_eventually_finishes():
    drivers, circuits = load()
    qual = create_qualifying(drivers, circuits[0])
    steps = 0
    while not qual["finished"] and steps < 1000:
        advance_qualifying(qual, 10)
        steps += 1
    assert qual["finished"]
    assert steps <= 180
