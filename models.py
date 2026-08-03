from dataclasses import dataclass, field


@dataclass
class Team:
    id: int
    name: str
    engine: int
    aerodynamics: int
    reliability: int
    logo: str = ""
    color_primary: str = "#1F2937"
    color_secondary: str = "#374151"
    drivers_colors: dict = field(default_factory=dict)


@dataclass
class Driver:
    name: str
    talent: int
    team: Team
    country: str = ""


@dataclass
class Circuit:
    name: str
    engine_factor: float
    aero_factor: float
    base_lap_time: float
    laps: int
    pit_loss: float = 22.0
    rain_chance_multiplier: float = 1.0
