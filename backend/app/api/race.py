from typing import Dict, Optional
import json

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response

from backend.app.schemas.race_state import RaceState
from backend.app.services.race_service import RaceService
from backend.app.services.session_service import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    session_store,
)

router = APIRouter(prefix="/race", tags=["Race"])


def get_session_service(request: Request, response: Response) -> RaceService:
    """Resolve the calling browser's own independent game world.

    A ``session_id`` cookie (set on first visit) maps to a dedicated
    ``RaceService`` so every visitor plays their own season and holds their own
    AI key — nothing is shared through a server singleton anymore.
    """
    session_id = request.cookies.get(COOKIE_NAME)
    service = session_store.touch(session_id) if session_id else None
    if service is not None:
        return service

    # Fresh visitor (or one whose idle session was evicted): mint an
    # unguessable id and a brand-new world.
    new_id = session_store.new_session_id()
    response.set_cookie(
        COOKIE_NAME,
        new_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
        # Only mark Secure when actually on HTTPS (Render terminates TLS and
        # forwards X-Forwarded-Proto; local dev over http must stay cookie-able).
        secure=request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https",
    )
    return session_store.create(new_id)


@router.get("/state", response_model=RaceState)
def get_state(svc: RaceService = Depends(get_session_service)):
    """Return the calling session's current race state."""
    return svc.get_state()


@router.get("/teams")
def list_teams(svc: RaceService = Depends(get_session_service)):
    """Return available teams and their drivers for team selection."""
    return svc.list_teams()


@router.post("/reset", response_model=RaceState)
def reset(svc: RaceService = Depends(get_session_service)):
    """Reset the calling session to a fresh pre-season state (team selection)."""
    svc.reset()
    return svc.get_state()


@router.post("/start", response_model=RaceState)
def start_season(
    payload: Dict = Body(...),
    svc: RaceService = Depends(get_session_service),
):
    """Start the season/race with the chosen player team.

    Expected body: {"team_id": <int>, "ai_api_key": "<optional key>"}

    The API key (if given) opts this session's AI opponents into the LLM
    decision engine. It is held in memory only, never saved, and never returned
    in any response.
    """
    team_id = payload.get("team_id")
    if team_id is None:
        raise HTTPException(status_code=400, detail="team_id is required")

    try:
        svc.start_season(team_id, payload.get("ai_api_key"))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid team_id")

    return svc.get_state()


@router.post("/next-lap", response_model=RaceState)
def next_lap(
    commands: Optional[Dict[str, str]] = Body(None),
    svc: RaceService = Depends(get_session_service),
):
    """Advance the calling session's race by one lap.

    Optional JSON body: { "Driver Name": "Stay Out|Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    cmds = commands or {}
    engine_cmds: Dict[str, str] = {}
    for driver_name, choice in cmds.items():
        if not choice or str(choice).strip().lower() == "stay out":
            continue
        # The engine normalizes English/PT-BR tyre names itself.
        engine_cmds[driver_name] = str(choice)
    return svc.next_lap(engine_cmds)


@router.post("/qualifying/tick", response_model=RaceState)
def qualifying_tick(
    payload: Optional[Dict[str, int]] = Body(None),
    svc: RaceService = Depends(get_session_service),
):
    """Advance the calling session's qualifying session.

    Optional JSON body: { "seconds": <int> } (defaults to 10 sim-seconds).
    """
    seconds = (payload or {}).get("seconds", 10)
    return svc.qualifying_tick(seconds)


@router.post("/qualifying/skip", response_model=RaceState)
def qualifying_skip(
    payload: Optional[Dict[str, str]] = Body(None),
    svc: RaceService = Depends(get_session_service),
):
    """Fast-forward the calling session's qualifying to a phase or to the end.

    Optional JSON body: { "phase": "Q2" | "Q3" | "end" }
    """
    phase = (payload or {}).get("phase")
    return svc.qualifying_skip(phase)


@router.post("/start-race", response_model=RaceState)
def start_race(
    starting_tyres: Optional[Dict[str, str]] = Body(None),
    svc: RaceService = Depends(get_session_service),
):
    """Start the calling session's race from the qualifying grid.

    Optional JSON body: { "Driver Name": "Soft|Medium|Hard|Intermediate|Wet", ... }
    """
    return svc.start_race(starting_tyres or {})


@router.post("/continue", response_model=RaceState)
def continue_race(svc: RaceService = Depends(get_session_service)):
    """Continue to the next grand prix (awards points and advances circuits)."""
    try:
        return svc.continue_to_next_race()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/standings")
def standings(svc: RaceService = Depends(get_session_service)):
    return {
        "standings": svc.get_standings(),
        "constructor_standings": svc.get_constructor_standings(),
        "season_results": svc.get_season_results(),
        "season_finished": svc.is_season_finished(),
    }


@router.get("/calendar")
def calendar(svc: RaceService = Depends(get_session_service)):
    return svc.get_calendar()


@router.get("/analytics")
def analytics(svc: RaceService = Depends(get_session_service)):
    return svc.analytics()


@router.get("/export")
def export_csv(svc: RaceService = Depends(get_session_service)):
    csv_text = svc.export_csv()
    return {"csv": csv_text}


@router.get("/save/meta")
def save_meta(svc: RaceService = Depends(get_session_service)):
    """Describe the calling session's saved game for the Settings UI."""
    return svc.save_meta()


@router.get("/save/data")
def export_save(svc: RaceService = Depends(get_session_service)):
    """Return the calling session's game state as a JSON-able object.

    Used by the client to keep each player's save in their own browser
    (localStorage) instead of a shared server-side game world.
    """
    return svc.export_save()


@router.post("/save")
def save_game(svc: RaceService = Depends(get_session_service)):
    """Persist the calling session's game state to its own on-disk save."""
    return svc.save_game()


@router.post("/load")
def load_game(
    payload: Optional[Dict] = Body(None),
    svc: RaceService = Depends(get_session_service),
):
    """Restore a saved game state into the calling session.

    Optional JSON body: a save object (e.g. one kept in the browser's
    localStorage). Without a body the session's on-disk save file is restored.
    """
    try:
        return svc.load_game(payload)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=str(e))