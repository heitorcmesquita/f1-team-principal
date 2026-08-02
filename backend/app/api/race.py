from typing import Dict, Optional

from fastapi import APIRouter, Body, HTTPException

from backend.app.services.race_service import race_service

router = APIRouter(prefix="/race", tags=["Race"])


@router.get("/state")
def get_state():
    """Return current race state."""
    return race_service.get_state()


@router.get("/teams")
def list_teams():
    """Return available teams and their drivers for team selection."""
    return race_service.list_teams()


@router.post("/start")
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


@router.post("/next-lap")
def next_lap(commands: Optional[Dict[str, str]] = Body(None)):
    """Advance the race by one lap.

    Optional JSON body: { "Driver Name": "Stay Out|Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    if not commands:
        return race_service.next_lap({})

    # Map frontend labels to engine tyre names
    tyre_map = {
        "Stay Out": None,
        "stay out": None,
        "Soft": "macio",
        "soft": "macio",
        "Medium": "medio",
        "medium": "medio",
        "Hard": "duro",
        "hard": "duro",
        "Intermediate": "intermediario",
        "intermediate": "intermediario",
        "Wet": "chuva",
        "wet": "chuva",
    }

    engine_cmds: Dict[str, str] = {}
    for driver_name, choice in commands.items():
        if choice is None:
            continue
        mapped = tyre_map.get(choice, None)
        if mapped:
            engine_cmds[driver_name] = mapped
    return race_service.next_lap(engine_cmds)


@router.post("/qualifying/tick")
def qualifying_tick(payload: Optional[Dict[str, int]] = Body(None)):
    """Advance the current qualifying session.

    Optional JSON body: { "seconds": <int> } (defaults to 10 sim-seconds).
    """
    seconds = (payload or {}).get("seconds", 10)
    return race_service.qualifying_tick(seconds)


@router.post("/qualifying/skip")
def qualifying_skip(payload: Optional[Dict[str, str]] = Body(None)):
    """Fast-forward qualifying to the start of a specific phase, or to the end.

    Optional JSON body: { "phase": "Q2" | "Q3" | "end" }
    """
    phase = (payload or {}).get("phase")
    return race_service.qualifying_skip(phase)


@router.post("/start-race")
def start_race(starting_tyres: Optional[Dict[str, str]] = Body(None)):
    """Start the race from the qualifying grid using the chosen starting tyres.

    Optional JSON body: { "Driver Name": "Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    return race_service.start_race(starting_tyres or {})


@router.post("/continue")
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
        "season_results": race_service._season_results,
        "season_finished": race_service._season_finished,
    }


@router.get("/analytics")
def analytics():
    return race_service.analytics()


@router.get("/export")
def export_csv():
    csv_text = race_service.export_csv()
    return {"csv": csv_text}
