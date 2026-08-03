from typing import List

from backend.app.schemas.race_state import DriverState


def build_driver_state(state) -> DriverState:
    """Map a single engine driver-state dict to the API DriverState model.

    Single source of truth for every place the API exposes a driver's live
    state (race classification, stored season summaries, etc.).
    """
    driver = state["driver"]
    return DriverState(
        position=state.get("position", 0),
        driver=driver.name,
        team=driver.team.name,
        tyre=state.get("tyre", ""),
        tyre_age=state.get("tyre_age", 0),
        gap=state.get("gap"),
        interval=state.get("interval"),
        laps_completed=state.get("laps_completed", 0),
        last_lap=state.get("last_lap"),
        best_lap=state.get("best_lap"),
        status=state.get("status", ""),
        position_delta=state.get("position_delta", 0),
        position_delta_reason=state.get("position_delta_reason", "Unchanged"),
        risk_level=state.get("risk_level", "Low"),
        pit_stops=state.get("pit_stops", 0),
        compounds_used=list(state.get("compounds_used", [])),
    )


def build_classification(states) -> List[DriverState]:
    return [build_driver_state(state) for state in states]
