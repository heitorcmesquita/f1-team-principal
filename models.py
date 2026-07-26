from dataclasses import dataclass
@dataclass
class Team: id:int; name:str; engine:int; aerodynamics:int; reliability:int
@dataclass
class Driver: name:str; talent:int; team:Team
@dataclass
class Circuit: name:str; engine_factor:float; aero_factor:float; base_lap_time:float; laps:int
