from pydantic import BaseModel
from typing import List, Optional


class DriverState(BaseModel):
    position: int
    driver: str
    team: str
    tyre: str
    tyre_age: int
    gap: Optional[float]
    last_lap: float
    best_lap: float
    status: str = "Running"
    position_delta: int = 0
    position_delta_reason: Optional[str] = "Unchanged"
    risk_level: Optional[str] = "Low"
    pit_stops: int = 0


class RaceEvent(BaseModel):
    lap: int
    message: str


class RaceState(BaseModel):
    race_name: str
    lap: int
    total_laps: int

    weather: str
    # Rain chance (%) within 5/10/20 laps: {"5": x, "10": y, "20": z}
    weather_forecast: Optional[dict] = None
    strategy_locked: bool = False
    safety_car: bool = False
    red_flag: bool = False

    finished: bool

    # Weekend phase: selection | qualifying | tyre_selection | race | season_finished
    phase: str = "race"
    # Live qualifying snapshot (phase == "qualifying")
    qualifying: Optional[dict] = None
    # Starting grid (phase == "tyre_selection" / "race")
    grid: Optional[list] = None
    starting_tyres: Optional[dict] = None
    # The team the player controls, if a season is in progress
    player_team_id: Optional[int] = None

    classification: List[DriverState]

    events: List[RaceEvent]
