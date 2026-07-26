import json
from pathlib import Path
from models import Team,Driver,Circuit
def load():
 t={x['id']:Team(**x) for x in json.loads(Path('data/static/teams.json').read_text())}
 d=[Driver(x['name'],x['talent'],t[x['team_id']]) for x in json.loads(Path('data/static/drivers.json').read_text())]
 c=[Circuit(**x) for x in json.loads(Path('data/static/circuits.json').read_text())]
 return d,c
