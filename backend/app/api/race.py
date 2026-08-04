from typing import Dict, Optional
import json

from fastapi import APIRouter, Body, HTTPException

from backend.app.schemas.race_state import RaceState
from backend.app.services.race_service import race_service

router = APIRouter(prefix="/race", tags=["Race"])


@router.get("/state", response_model=RaceState)
def get_state():
    """Return current race state."""
    return race_service.get_state()


@router.get("/teams")
def list_teams():
    """Return available teams and their drivers for team selection."""
    return race_service.list_teams()


@router.post("/reset", response_model=RaceState)
def reset():
    """Reset the server to a fresh pre-season state (team selection)."""
    race_service.reset()
    return race_service.get_state()


@router.post("/start", response_model=RaceState)
def start_season(payload: Dict[str, int] = Body(...)):
    """Start the season/race with chosen player team.

    Expected body: {"team_id": <int>}
    """
    team_id = payload.get("team_id")
    if team_id is None:
        raise HTTPException(status_code=400, detail="team_id is required")

    try:
        race_service.start_season(team_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid team_id")

    return race_service.get_state()


@router.post("/next-lap", response_model=RaceState)
def next_lap(commands: Optional[Dict[str, str]] = Body(None)):
    """Advance the race by one lap.

    Optional JSON body: { "Driver Name": "Stay Out|Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    cmds = commands or {}
    engine_cmds: Dict[str, str] = {}
    for driver_name, choice in cmds.items():
        if not choice or str(choice).strip().lower() == "stay out":
            continue
        # The engine normalizes English/PT-BR tyre names itself.
        engine_cmds[driver_name] = str(choice)
    return race_service.next_lap(engine_cmds)


@router.post("/qualifying/tick", response_model=RaceState)
def qualifying_tick(payload: Optional[Dict[str, int]] = Body(None)):
    """Advance the current qualifying session.

    Optional JSON body: { "seconds": <int> } (defaults to 10 sim-seconds).
    """
    seconds = (payload or {}).get("seconds", 10)
    return race_service.qualifying_tick(seconds)


@router.post("/qualifying/skip", response_model=RaceState)
def qualifying_skip(payload: Optional[Dict[str, str]] = Body(None)):
    """Fast-forward qualifying to the start of a specific phase, or to the end.

    Optional JSON body: { "phase": "Q2" | "Q3" | "end" }
    """
    phase = (payload or {}).get("phase")
    return race_service.qualifying_skip(phase)


@router.post("/start-race", response_model=RaceState)
def start_race(starting_tyres: Optional[Dict[str, str]] = Body(None)):
    """Start the race from the qualifying grid using the chosen starting tyres.

    Optional JSON body: { "Driver Name": "Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    return race_service.start_race(starting_tyres or {})


@router.post("/continue", response_model=RaceState)
def continue_race():
    """Continue to next grand prix (awards points and advances circuits)."""
    try:
        return race_service.continue_to_next_race()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/standings")
def standings():
    return {
        "standings": race_service.get_standings(),
        "constructor_standings": race_service.get_constructor_standings(),
        "season_results": race_service.get_season_results(),
        "season_finished": race_service.is_season_finished(),
    }


@router.get("/calendar")
def calendar():
    return race_service.get_calendar()


@router.get("/analytics")
def analytics():
    return race_service.analytics()


@router.get("/export")
def export_csv():
    csv_text = race_service.export_csv()
    return {"csv": csv_text}


@router.get("/save/meta")
def save_meta():
    """Describe the saved game for the Settings UI (does not require a live season)."""
    return race_service.save_meta()


@router.get("/save/data")
def export_save():
    """Return the current game state as a serializable JSON object.

    Used by the client to keep each player's save in their own browser
    (localStorage) instead of a shared server-side game world.
    """
    return race_service.export_save()


@router.post("/save")
def save_game():
    """Persist the current game state to disk."""
    return race_service.save_game()


@router.post("/load")
def load_game(payload: Optional[Dict] = Body(None)):
    """Restore a saved game state.

    Optional JSON body: a save object (e.g. one kept in the browser's
    localStorage). Without a body the on-disk save file is restored.
    """
    try:
        return race_service.load_game(payload)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
