import json
from pathlib import Path
from models import Team,Driver,Circuit
def load():
 teams_data = json.loads(Path('data/static/teams.json').read_text())
 t = {}
 for x in teams_data:
  drivers_colors = x.get('drivers_colors', {})
  t[x['id']] = Team(
    id=x['id'],
    name=x['name'],
    engine=x['engine'],
    aerodynamics=x['aerodynamics'],
    reliability=x['reliability'],
    logo=x.get('logo', ''),
    color_primary=x.get('color_primary', '#1F2937'),
    color_secondary=x.get('color_secondary', '#374151'),
    drivers_colors=drivers_colors if drivers_colors else {}
  )
 d=[Driver(x['name'],x['talent'],t[x['team_id']],country=x.get('country','')) for x in json.loads(Path('data/static/drivers.json').read_text())]
 c=[Circuit(**x) for x in json.loads(Path('data/static/circuits.json').read_text())]
 return d,c
