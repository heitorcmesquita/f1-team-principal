import sys
from pathlib import Path
import pytest

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.services.race_service import RaceService
from backend.app.services.save_service import SAVE_PATH


@pytest.fixture(autouse=True)
def clean_save_file():
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()
    yield
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()


def test_save_load_restores_mid_race():
    svc = RaceService()
    svc.start_season(1)
    svc.qualifying_skip()
    svc.start_race({})
    for _ in range(12):
        svc.next_lap({})
    before = svc.get_state()

    meta = svc.save_game()
    assert meta["exists"] is True
    assert meta["lap"] == 12

    # Fresh service simulates a server restart.
    restored = RaceService()
    after = restored.load_game()
    assert after.lap == before.lap
    assert after.phase == before.phase
    assert after.race_name == before.race_name
    assert after.player_team_id == before.player_team_id
    assert len(after.classification) == len(before.classification)
    for a, b in zip(before.classification, after.classification):
        assert a.driver == b.driver
        assert a.position == b.position
        assert a.tyre == b.tyre
        assert a.tyre_age == b.tyre_age
        assert a.pit_stops == b.pit_stops
    assert len(after.events) == len(before.events)

    # The engine must keep working on the restored state.
    restored.next_lap({})
    assert restored.get_state().lap == before.lap + 1


def test_save_load_preserves_season_results_and_standings():
    svc = RaceService()
    svc.start_season(1)
    svc.qualifying_skip()
    svc.start_race({})
    total = svc.race["circuit"].laps
    for _ in range(total):
        svc.next_lap({})
    assert svc.get_state().finished is True
    assert any(v > 0 for v in svc.season._standings.values())
    assert len(svc.season._season_results) == 1

    svc.save_game()
    restored = RaceService()
    restored.load_game()

    assert restored.get_state().finished is True
    assert restored.season._standings == svc.season._standings
    assert len(restored.season._season_results) == 1
    podium = restored.get_calendar()["results"][0]["podium"]
    assert len(podium) == 3


def test_save_during_tyre_selection_and_qualifying():
    svc = RaceService()
    svc.start_season(2)
    svc.qualifying_skip()  # -> tyre_selection
    svc.save_game()
    restored = RaceService()
    state = restored.load_game()
    assert state.phase == "tyre_selection"
    assert len(state.grid or []) == len(svc.drivers)

    svc2 = RaceService()
    svc2.start_season(3)  # -> qualifying
    svc2.save_game()
    restored2 = RaceService()
    state2 = restored2.load_game()
    assert state2.phase == "qualifying"
    assert state2.qualifying is not None


def test_browser_save_round_trip_and_reset():
    """Per-player worlds: export -> reset -> restore-from-blob keeps the engine working."""
    svc = RaceService()
    svc.start_season(1)
    svc.qualifying_skip()
    svc.start_race({})
    for _ in range(3):
        svc.next_lap({})
    blob = svc.export_save()
    assert blob["phase"] == "race"
    assert blob["race"]["lap"] == 3

    # A new visitor (no browser save) must not inherit the previous game world.
    fresh = RaceService()
    fresh.reset()
    assert fresh.get_state().phase == "selection"
    assert fresh.race is None
    assert fresh.player_team is None

    # Returning player restores their own world from the browser blob.
    restored = fresh.load_game(blob)
    assert restored.phase == "race"
    assert restored.lap == 3
    assert restored.player_team_id == 1

    # Engine still advances on the restored state.
    restored = fresh.next_lap({})
    assert restored.lap == 4
