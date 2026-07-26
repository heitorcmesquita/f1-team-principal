import random

TYRE_RULES={
 "macio":{"pace":-0.85,"deg":1.9,"wet_low":0,"wet_high":5,"dnf":0.0},
 "medio":{"pace":-0.45,"deg":1.2,"wet_low":0,"wet_high":5,"dnf":0.05},
 "duro":{"pace":0.0,"deg":0.8,"wet_low":0,"wet_high":5,"dnf":0.08},
 "intermediario":{"pace":0.35,"deg":1.1,"wet_low":6,"wet_high":30,"dnf":0.12},
 "chuva":{"pace":1.1,"deg":1.0,"wet_low":31,"wet_high":100,"dnf":0.18},
}
DRY_START=("macio","medio","duro")
WET_START=("intermediario","chuva")

def initial_tyre(track_wetness):
 return "chuva" if track_wetness>30 else ("intermediario" if track_wetness>5 else random.choice(DRY_START))

def create_race(drivers,circuit,player_team):
 wetness=_starting_wetness()
 weather=_weather_label(wetness)
 states=[_create_driver_state(d,wetness) for d in drivers]
 return {
  "circuit":circuit,
  "player_team":player_team,
  "lap":0,
  "track_wetness":wetness,
  "weather":weather,
  "rain_state":_initial_rain_state(wetness),
  "states":states,
 }

def run_lap(race_state,player_commands):
 race_state["lap"]+=1
 events=[]
 _apply_player_commands(race_state,player_commands,events)
 _apply_ai_strategy(race_state,events)
 _update_weather(race_state,events)
 running_before=sorted([s for s in race_state["states"] if s["status"]=="Running"],key=lambda s:(s["position"] if s["position"] else 999,s["total_time"]))
 if not any(state["position"] for state in running_before):
  running_before=sorted(running_before,key=lambda s:s["total_time"])
 lap_data=[]
 for state in race_state["states"]:
  if state["status"]!="Running":
   continue
  if state["pit_pending"]:
   _do_pit_stop(state,events)
  lap_time,dnf_reason=_simulate_driver_lap(state,race_state["circuit"],race_state["track_wetness"])
  if dnf_reason:
   state["status"]=dnf_reason
   state["last_lap"]=None
   state["gap"]=None
   state["interval"]=None
   events.append(f"{state['driver'].name} abandonou: {dnf_reason}")
   continue
  lap_data.append({"state":state,"lap_time":lap_time,"projected_total":state["total_time"]+lap_time})
  state["tyre_age"]+=1
  state["pit_pending"]=None
 _resolve_on_track_order(running_before,lap_data,events)
 finished=[s for s in race_state["states"] if s["status"]=="Running"]
 finished.sort(key=lambda s:s["total_time"])
 for pos,state in enumerate(finished,1):
  state["position"]=pos
  state["gap"]=0.0 if pos==1 else state["total_time"]-finished[0]["total_time"]
  state["interval"]=0.0 if pos==1 else state["total_time"]-finished[pos-2]["total_time"]
 retired=[s for s in race_state["states"] if s["status"]!="Running"]
 retired.sort(key=lambda s:s["laps_completed"],reverse=True)
 for idx,state in enumerate(retired,len(finished)+1):
  state["position"]=idx
  state["gap"]=None
  state["interval"]=None
 return _snapshot(race_state,events)

def is_race_finished(race_state):
 if race_state["lap"]>=race_state["circuit"].laps:
  return True
 return not any(s["status"]=="Running" for s in race_state["states"])

def final_classification(race_state):
 ordered=sorted(race_state["states"],key=lambda s:(s["status"]!="Running",-s["laps_completed"],s["total_time"] if s["total_time"] else 10**9))
 ordered.sort(key=lambda s:s["position"])
 return ordered

def _create_driver_state(driver,track_wetness):
 return {
  "driver":driver,
  "total_time":0.0,
  "last_lap":None,
  "tyre":initial_tyre(track_wetness),
  "tyre_age":0,
  "status":"Running",
  "laps_completed":0,
  "position":0,
  "gap":None,
  "interval":None,
  "pit_pending":None,
  "pit_stops":0,
 }

def _starting_wetness():
 roll=random.randint(1,100)
 if roll<=90:return 0
 if roll<=97:return random.randint(6,30)
 return random.randint(31,100)

def _weather_label(wetness):
 if wetness<=5:return "Seco"
 if wetness<=30:return "Umido"
 if wetness<70:return "Chuva leve"
 return "Chuva forte"

def _apply_player_commands(race_state,player_commands,events):
 for state in race_state["states"]:
  if state["driver"].team.id!=race_state["player_team"].id or state["status"]!="Running":
   continue
  new_tyre=player_commands.get(state["driver"].name)
  if new_tyre:
   state["pit_pending"]=new_tyre
   events.append(f"{state['driver'].name} vai parar para {new_tyre}.")

def _apply_ai_strategy(race_state,events):
 for state in race_state["states"]:
  if state["driver"].team.id==race_state["player_team"].id or state["status"]!="Running" or state["pit_pending"]:
   continue
  suggested=_best_tyre_for_conditions(race_state["track_wetness"])
  needs_weather_swap=_wet_penalty(race_state["track_wetness"],state["tyre"])>=1.6
  needs_wear_swap=state["tyre_age"]>=_wear_limit(state["tyre"])
  late_splash=race_state["lap"]>race_state["circuit"].laps*0.7 and state["tyre"]=="macio" and state["tyre_age"]>=8
  if needs_weather_swap or needs_wear_swap or late_splash:
   if suggested==state["tyre"]:
    suggested=_fallback_dry_tyre(state["tyre"],race_state["track_wetness"])
   if suggested!=state["tyre"]:
    state["pit_pending"]=suggested
    events.append(f"{state['driver'].name} vai parar para {suggested}.")

def _update_weather(race_state,events):
 _evolve_rain_state(race_state,events)
 change=_wetness_delta(race_state["rain_state"],race_state["track_wetness"])
 race_state["track_wetness"]=max(0,min(100,race_state["track_wetness"]+change))
 new_weather=_weather_label(race_state["track_wetness"])
 if new_weather!=race_state["weather"]:
  race_state["weather"]=new_weather
  events.append(f"Clima mudou: {new_weather} ({race_state['track_wetness']}% molhado).")

def _do_pit_stop(state,events):
 state["tyre"]=state["pit_pending"]
 state["tyre_age"]=0
 state["pit_stops"]+=1
 events.append(f"{state['driver'].name} colocou pneu {state['tyre']}.")

def _simulate_driver_lap(state,circuit,track_wetness):
 tyre=TYRE_RULES[state["tyre"]]
 driver=state["driver"]
 driver_gain=driver.talent*0.035
 car_gain=(driver.team.engine*circuit.engine_factor+driver.team.aerodynamics*circuit.aero_factor)*0.022
 degradation=state["tyre_age"]*0.09*tyre["deg"]
 global_wet_slowdown=track_wetness*0.02
 wet_penalty=_wet_penalty(track_wetness,state["tyre"])
 noise=random.gauss(0,0.28)
 pit_loss=22.0 if state["pit_pending"] else 0.0
 lap_time=circuit.base_lap_time-driver_gain-car_gain+tyre["pace"]+degradation+global_wet_slowdown+wet_penalty+pit_loss+noise
 dnf_reason=_lap_dnf_event(driver.team.reliability,driver.talent,circuit.laps,track_wetness,degradation,wet_penalty,state["tyre"],tyre["dnf"])
 if dnf_reason:
  return None,dnf_reason
 return lap_time,None

def _wet_penalty(track_wetness,tyre_name):
 tyre=TYRE_RULES[tyre_name]
 if tyre["wet_low"]<=track_wetness<=tyre["wet_high"]:
  return 0.0
 if track_wetness<tyre["wet_low"]:
  return (tyre["wet_low"]-track_wetness)*0.05
 return (track_wetness-tyre["wet_high"])*0.08

def _snapshot(race_state,events):
 ordered=sorted(race_state["states"],key=lambda s:s["position"])
 return {
  "lap":race_state["lap"],
  "laps":race_state["circuit"].laps,
  "weather":race_state["weather"],
  "track_wetness":race_state["track_wetness"],
  "table":ordered,
  "events":events,
 }

def _initial_rain_state(wetness):
 if wetness>30:return "forte"
 if wetness>5:return "leve"
 return "seco"

def _evolve_rain_state(race_state,events):
 state=race_state["rain_state"]
 roll=random.random()
 if state=="seco":
  if roll<0.015:
   race_state["rain_state"]="leve"
   events.append("Comecou a garoar.")
  return
 if state=="leve":
  if roll<0.08:
   race_state["rain_state"]="seco"
   events.append("A chuva parou.")
  elif roll<0.12:
   race_state["rain_state"]="forte"
   events.append("A chuva apertou.")
  return
 if roll<0.10:
  race_state["rain_state"]="leve"
  events.append("A chuva diminuiu.")

def _wetness_delta(rain_state,track_wetness):
 if rain_state=="seco":
  if track_wetness==0:return 0
  return -random.randint(2,6)
 if rain_state=="leve":
  if track_wetness<5:return random.randint(1,3)
  return random.randint(-1,3)
 return random.randint(3,8)

def _lap_dnf_event(reliability,talent,laps,track_wetness,degradation,wet_penalty,tyre_name,tyre_risk):
 mechanical=_race_to_lap_risk(0.02+(100-reliability)*0.005,max(1,laps))
 accident_base=0.003+max(0.0,degradation-1.2)*0.003+max(0.0,wet_penalty-0.6)*0.02+tyre_risk*0.004
 accident_skill=max(0.55,1.05-(talent-80)*0.012)
 accident=_race_to_lap_risk(min(0.08,accident_base*accident_skill),max(1,laps))
 aquaplane=_race_to_lap_risk(_aquaplane_race_risk(track_wetness,wet_penalty,tyre_name),max(1,laps))
 roll=random.random()
 if roll<mechanical:
  return "Falha mecanica"
 if roll<mechanical+accident:
  return "Acidente"
 if roll<mechanical+accident+aquaplane:
  return "Aquaplanagem"
 return None

def _race_to_lap_risk(race_risk,laps):
 return max(0.0,min(0.95,race_risk))/laps

def _aquaplane_race_risk(track_wetness,wet_penalty,tyre_name):
 if track_wetness<=30:
  return 0.0
 if tyre_name in ("macio","medio","duro"):
  return min(0.16,(track_wetness-30)*0.002+wet_penalty*0.025)
 if tyre_name=="intermediario" and track_wetness>=65:
  return min(0.07,(track_wetness-65)*0.0015+wet_penalty*0.012)
 return 0.0

def _resolve_on_track_order(running_before,lap_data,events):
 data_by_id={entry["state"]["driver"].name:entry for entry in lap_data}
 ordered=[]
 for state in running_before:
  if state["status"]!="Running":
   continue
  entry=data_by_id.get(state["driver"].name)
  if entry:
   ordered.append(entry)
 for entry in lap_data:
  if entry not in ordered:
   ordered.append(entry)
 if not ordered:
  return
 resolved=[ordered[0]]
 for entry in ordered[1:]:
  front=resolved[-1]
  front_state=front["state"]
  state=entry["state"]
  start_gap=max(0.0,state["total_time"]-front_state["total_time"])
  if entry["projected_total"]<front["projected_total"] and start_gap<1.0:
   if _overtake_succeeds(state["driver"].talent,start_gap):
    resolved[-1],entry=entry,front
    events.append(f"{state['driver'].name} ultrapassou {front_state['driver'].name}.")
   else:
    entry["projected_total"]=front["projected_total"]+random.uniform(0.12,0.45)
    entry["lap_time"]=entry["projected_total"]-state["total_time"]
  resolved.append(entry)
 for entry in resolved:
  state=entry["state"]
  state["total_time"]=entry["projected_total"]
  state["last_lap"]=entry["lap_time"]
  state["laps_completed"]=state["laps_completed"]+1

def _overtake_succeeds(talent,start_gap):
 chance=0.18+max(0,talent-80)*0.012+(1.0-start_gap)*0.08
 return random.random()<min(0.82,max(0.12,chance))

def _best_tyre_for_conditions(track_wetness):
 if track_wetness>30:return "chuva"
 if track_wetness>5:return "intermediario"
 if track_wetness<=2:return "macio"
 if track_wetness<=4:return "medio"
 return "duro"

def _wear_limit(tyre_name):
 return {"macio":10,"medio":16,"duro":22,"intermediario":18,"chuva":20}[tyre_name]

def _fallback_dry_tyre(current_tyre,track_wetness):
 if track_wetness>30:return "chuva"
 if track_wetness>5:return "intermediario"
 if current_tyre=="macio":return "medio"
 if current_tyre=="medio":return "duro"
 if current_tyre=="duro" and track_wetness==0:return "macio"
 return "duro"
