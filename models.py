from dataclasses import dataclass
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
  drivers_colors: dict = None

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
