"""Serialization helpers for the save/load feature.

The whole game lives in memory as a graph of dicts plus live object references
(Driver, Team, Circuit dataclasses). JSON can't store those directly, so this
module converts the object graph to tagged JSON structures and back:

  - Driver    -> {"$type": "driver",  "name": ...}
  - Team      -> {"$type": "team",    "id": ...}
  - Circuit   -> {"$type": "circuit", "name": ...}
  - DriverState -> {"$type": "driver_state", "data": {...}}

On load the tags are resolved back to the live objects using lookup maps built
from the static drivers/circuits data.
"""
import json
import random
from pathlib import Path

from models import Circuit, Driver, Team
from backend.app.schemas.race_state import DriverState

SAVE_PATH = Path("data/savegame.json")


def _tag(obj):
    if isinstance(obj, Driver):
        return {"$type": "driver", "name": obj.name}
    if isinstance(obj, Circuit):
        return {"$type": "circuit", "name": obj.name}
    if isinstance(obj, Team):
        return {"$type": "team", "id": obj.id}
    # The ad-hoc team-like object built when a team reference can't be found.
    if hasattr(obj, "id") and hasattr(obj, "name") and hasattr(obj, "engine"):
        return {"$type": "team", "id": obj.id}
    if isinstance(obj, DriverState):
        return {"$type": "driver_state", "data": obj.model_dump()}
    return None


def _to_jsonable(obj):
    """Recursively convert a value so it can be written as JSON.

    The race's `random.Random` instance is dropped (dict key "rng"); a fresh
    RNG is installed on load.
    """
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items() if k != "rng"}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    tag = _tag(obj)
    if tag is not None:
        return tag
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def _from_jsonable(obj, drivers_by_name, teams_by_id, circuits_by_name):
    if isinstance(obj, dict):
        if "$type" in obj:
            kind = obj["$type"]
            if kind == "driver":
                return drivers_by_name.get(obj["name"])
            if kind == "team":
                return teams_by_id.get(obj["id"])
            if kind == "circuit":
                return circuits_by_name.get(obj["name"])
            if kind == "driver_state":
                return DriverState(**obj["data"])
        return {k: _from_jsonable(v, drivers_by_name, teams_by_id, circuits_by_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_jsonable(x, drivers_by_name, teams_by_id, circuits_by_name) for x in obj]
    return obj


def build_lookup(drivers, circuits):
    """Build name/id -> object maps for restoring references from a save."""
    drivers_by_name = {d.name: d for d in drivers}
    teams_by_id = {}
    for d in drivers:
        tid = getattr(d.team, "id", None)
        if tid is not None and tid not in teams_by_id:
            teams_by_id[tid] = d.team
    circuits_by_name = {c.name: c for c in circuits}
    return drivers_by_name, teams_by_id, circuits_by_name


def minimal_qualifying(wetness, weather):
    """A placeholder qualifying dict for phases that only need weekend weather."""
    return {"track_wetness": wetness, "weather": weather, "finished": True}
