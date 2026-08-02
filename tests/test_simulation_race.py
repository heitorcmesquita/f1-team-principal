import sys
from pathlib import Path
import pytest

# Ensure root is in sys.path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from utils import load
from simulation.race import (
    create_race,
    run_lap,
    is_race_finished,
    final_classification,
    normalize_tyre,
    tyre_label,
    _wet_penalty,
    _dnf_lap_risks,
)

def test_normalize_tyre():
    assert normalize_tyre("macio") == "soft"
    assert normalize_tyre("medio") == "medium"
    assert normalize_tyre("médio") == "medium"
    assert normalize_tyre("duro") == "hard"
    assert normalize_tyre("intermediario") == "intermediate"
    assert normalize_tyre("chuva") == "wet"
    assert normalize_tyre("SOFT") == "soft"
    assert normalize_tyre("  Hard  ") == "hard"

def test_tyre_label():
    assert tyre_label("macio") == "Soft"
    assert tyre_label("chuva") == "Wet"
    assert tyre_label("medium") == "Medium"

def test_create_race():
    drivers, circuits = load()
    player_team = drivers[0].team
    circuit = circuits[0]
    race = create_race(drivers, circuit, player_team)
    
    assert race["circuit"] == circuit
    assert race["player_team"] == player_team
    assert race["lap"] == 0
    assert len(race["states"]) == len(drivers)

def test_run_single_lap():
    drivers, circuits = load()
    player_team = drivers[0].team
    circuit = circuits[0]
    race = create_race(drivers, circuit, player_team)
    
    snapshot = run_lap(race, {})
    assert snapshot["lap"] == 1
    assert len(snapshot["table"]) == len(drivers)
    
    first_driver = snapshot["table"][0]
    assert "position_delta_reason" in first_driver
    assert "risk_level" in first_driver
    assert "best_lap" in first_driver
    assert first_driver["best_lap"] is not None

def test_pit_stop_command():
    drivers, circuits = load()
    player_team = drivers[0].team
    circuit = circuits[0]
    race = create_race(drivers, circuit, player_team)
    
    player_driver_name = [s["driver"].name for s in race["states"] if s["driver"].team.id == player_team.id][0]
    
    snapshot = run_lap(race, {player_driver_name: "macio"})
    player_state = [s for s in race["states"] if s["driver"].name == player_driver_name][0]
    
    assert player_state["tyre"] == "soft"
    assert player_state["pit_stops"] == 1
    assert player_state["_pitted_this_lap"] is True
    assert "soft" in player_state["compounds_used"]

def test_wet_penalty():
    assert _wet_penalty(0, "soft") == 0.0
    assert _wet_penalty(0, "wet") > 0.0
    assert _wet_penalty(50, "wet") == 0.0
    assert _wet_penalty(50, "soft") > 0.0

def test_mandatory_compound_rule_dsq():
    drivers, circuits = load()
    player_team = drivers[0].team
    circuit = circuits[0]
    race = create_race(drivers, circuit, player_team)
    
    # Ensure dry race
    race["track_wetness"] = 0
    race["wet_race_declared"] = False
    
    # Force single driver to only use 1 compound
    target_state = race["states"][0]
    target_state["compounds_used"] = ["medium"]
    
    # Other drivers use 2 compounds
    for s in race["states"][1:]:
        s["compounds_used"] = ["medium", "hard"]
        
    classified = final_classification(race)
    dsq_drivers = [s for s in classified if s["status"] == "DSQ (Tyre Rule)"]
    assert len(dsq_drivers) == 1
    assert dsq_drivers[0]["driver"].name == target_state["driver"].name
