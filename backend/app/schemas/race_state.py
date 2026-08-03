from pydantic import BaseModel
from typing import List, Optional


class DriverState(BaseModel):
    position: int
    driver: str
    team: str
    tyre: str
    tyre_age: int
    gap: Optional[float] = None
    interval: Optional[float] = None
    laps_completed: int = 0
    last_lap: Optional[float] = None
    best_lap: Optional[float] = None
    status: str = "Running"
    position_delta: int = 0
    position_delta_reason: Optional[str] = "Unchanged"
    risk_level: Optional[str] = "Low"
    pit_stops: int = 0
    compounds_used: List[str] = []


class RaceEvent(BaseModel):
    lap: int
    message: str


class RaceState(BaseModel):
    race_name: str
    lap: int
    total_laps: int
    # Season context for the header/nav ("R5/24")
    circuit_index: int = 0
    total_circuits: int = 0

    weather: str
    # Rain chance (%) within 5/10/20 laps: {"5": x, "10": y, "20": z}
    weather_forecast: Optional[dict] = None
    safety_car: bool = False
    red_flag: bool = False

    finished: bool

    # Weekend phase: selection | qualifying | tyre_selection | race | season_finished
    phase: str = "race"
    # True once the final grand prix has been completed.
    season_finished: bool = False
    # Live qualifying snapshot (phase == "qualifying")
    qualifying: Optional[dict] = None
    # Starting grid. During "tyre_selection" this is a list of row dicts; during
    # the race it is the ordered list of driver names used to build the race.
    grid: Optional[list] = None
    starting_tyres: Optional[dict] = None
    # The team the player controls, if a season is in progress
    player_team_id: Optional[int] = None

    classification: List[DriverState]

    events: List[RaceEvent]
