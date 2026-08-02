import random

TYRE_RULES = {
 "soft":{"pace":-0.85,"deg":1.9,"wet_low":0,"wet_high":5,"dnf":0.0},
 "medium":{"pace":-0.45,"deg":1.2,"wet_low":0,"wet_high":5,"dnf":0.05},
 "hard":{"pace":0.0,"deg":0.8,"wet_low":0,"wet_high":5,"dnf":0.08},
 "intermediate":{"pace":0.35,"deg":1.1,"wet_low":6,"wet_high":30,"dnf":0.12},
 "wet":{"pace":1.1,"deg":1.0,"wet_low":31,"wet_high":100,"dnf":0.18},
}
DRY_START = ("soft","medium","hard")
WET_START = ("intermediate","wet")

NORMAL_PIT_LOSS = 22.0
SAFETY_CAR_WEAR_MULTIPLIER = 0.4
SAFETY_CAR_LAP_DELTA = 6.0
SAFETY_CAR_GAP_STEP = 0.5

TRAFFIC_PENALTY_PER_LAP = 0.18
TRAFFIC_PENALTY_CAP_LAPS = 5
TRAFFIC_OVERTAKE_BONUS_PER_LAP = 0.025
TRAFFIC_OVERTAKE_BONUS_CAP_LAPS = 5
TRAFFIC_CLOSING_SPEED_BONUS = 0.06
TRAFFIC_CLOSING_SPEED_CAP = 3.0

# Fresh tyres need a few laps to reach peak performance after a pit stop.
# The penalty decays exponentially so the first laps of a stint are never the fastest.
TYRE_WARMUP_LAPS = 2
TYRE_WARMUP_PENALTY = 2.2
# Total warm-up seconds lost across a fresh stint (used by AI cost estimates).
TYRE_WARMUP_COST = 2.9

# A tyre is "past its best" once per-lap degradation reaches this level.
TYRE_CLIFF_DEG = 0.9
# A voluntary stop must beat staying out by at least this many seconds to be worth it.
PIT_GAIN_MARGIN = 3.0

PERSONA_RISK_MIN = 0.6
PERSONA_RISK_MAX = 1.6
PERSONA_HESITATION_MIN = 0.10
PERSONA_HESITATION_MAX = 0.40

UNDERCUT_GAP_THRESHOLD = 3.0
UNDERCUT_RIVAL_WEAR_RATIO = 0.55
UNDERCUT_MIN_TYRE_AGE = 5
COVER_GAP_THRESHOLD = 3.0
COVER_MIN_TYRE_AGE = 4

# Tactical pit behaviour
SC_PIT_MIN_AGE_RATIO = 0.45
SC_PIT_LOSS_TOLERANCE = 8.0
SC_GAMBLE_CHANCE = 0.05
SC_GAMBLE_WINDOW = 0.65
HOLD_AT_CLIFF_CHANCE = 0.12

RISK_LOW_THRESHOLD = 0.01
RISK_MEDIUM_THRESHOLD = 0.04

TYRE_ALIAS_MAP = {
 "macio": "soft",
 "medio": "medium",
 "médio": "medium",
 "duro": "hard",
 "intermediario": "intermediate",
 "intermediário": "intermediate",
 "chuva": "wet",
 "soft": "soft",
 "medium": "medium",
 "hard": "hard",
 "intermediate": "intermediate",
 "wet": "wet",
}

def normalize_tyre(name: str) -> str:
 if not name:
  return "medium"
 cleaned = str(name).strip().lower()
 return TYRE_ALIAS_MAP.get(cleaned, cleaned)

def tyre_label(tyre_name):
 tyre_key = normalize_tyre(tyre_name)
 return {"soft":"Soft","medium":"Medium","hard":"Hard","intermediate":"Intermediate","wet":"Wet"}.get(tyre_key, str(tyre_name).capitalize())

def initial_tyre(track_wetness):
 return "wet" if track_wetness>30 else ("intermediate" if track_wetness>5 else random.choice(DRY_START))

def projected_pace(driver, circuit, tyre="soft"):
 """Deterministic lap-time estimate (no noise) shared by race & qualifying logic."""
 tyre_key = normalize_tyre(tyre)
 tyre = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
 talent = getattr(driver, "talent", 80)
 team = driver.team
 engine = getattr(team, "engine", 50)
 aero = getattr(team, "aerodynamics", 50)
 driver_gain = talent * 0.035
 car_gain = (engine * getattr(circuit, "engine_factor", 0.5) + aero * getattr(circuit, "aero_factor", 0.5)) * 0.022
 return circuit.base_lap_time - driver_gain - car_gain + tyre["pace"]

def qualifying_lap_time(driver, circuit, track_wetness, tyre="soft", evolution_bonus=0.0, traffic_penalty=0.0):
 """Single flying-lap time for qualifying. Mirrors the race pace model (fresh tyre, no pit/SC)."""
 tyre_key = normalize_tyre(tyre)
 global_wet_slowdown = track_wetness * 0.02
 wet_penalty = _wet_penalty(track_wetness, tyre_key)
 noise = random.gauss(0, 0.28)
 return projected_pace(driver, circuit, tyre) + global_wet_slowdown + wet_penalty + evolution_bonus + traffic_penalty + noise

def create_race(drivers,circuit,player_team,grid=None,starting_tyres=None,track_wetness=None):
 wetness = _starting_wetness() if track_wetness is None else track_wetness
 weather = _weather_label(wetness)
 states = [_create_driver_state(d,wetness) for d in drivers]
 if grid:
  grid_order = {name:idx for idx,name in enumerate(grid)}
  states.sort(key=lambda s: grid_order.get(s["driver"].name, len(grid)))
  for i,state in enumerate(states,1):
   state["position"] = i
   state["starting_position"] = i
 else:
  for state in states:
   state["starting_position"] = None
 if starting_tyres:
  for state in states:
   raw = starting_tyres.get(state["driver"].name)
   if raw:
    tyre = normalize_tyre(raw)
    state["tyre"] = tyre
    state["compounds_used"] = [tyre]
 return {
  "circuit":circuit,
  "player_team":player_team,
  "lap":0,
  "track_wetness":wetness,
  "weather":weather,
  "rain_state":_initial_rain_state(wetness),
  "wet_race_declared": wetness > 5,
  "states":states,
  "safety_car":False,
  "safety_car_timer":0,
  "safety_car_laps":0,
  "red_flag_stoppage":False,
  "weather_grace_laps":0,
  "team_personas":_build_team_personas(drivers,player_team)
 }

def _build_team_personas(drivers,player_team):
 personas = {}
 for d in drivers:
  team = d.team
  if team.id==player_team.id or team.id in personas:
   continue
  personas[team.id] = {
   "risk_tolerance":random.uniform(PERSONA_RISK_MIN,PERSONA_RISK_MAX),
   "hesitation":random.uniform(PERSONA_HESITATION_MIN,PERSONA_HESITATION_MAX),
   "stint_bias":random.uniform(-1.0,1.0),
  }
 return personas

def run_lap(race_state,player_commands):
 if race_state["red_flag_stoppage"]:
  return _run_red_flag_stoppage_lap(race_state,player_commands)
 race_state["lap"] += 1
 events = []
 previous_positions = {s["driver"].name:s.get("position",0) for s in race_state["states"]}
 if race_state["safety_car"]:
  race_state["safety_car_laps"] = race_state.get("safety_car_laps", 0) + 1
 for state in race_state["states"]:
  state["_pitted_this_lap"] = False
  state["_overtook"] = False
  state["_overtaken"] = False
 if race_state.get("weather_grace_laps", 0) > 0:
  race_state["weather_grace_laps"] = 0
  events.append("All cars stay out for a lap as conditions change.")
 else:
  _apply_player_commands(race_state,player_commands,events)
  _apply_ai_strategy(race_state,events)
 _update_weather(race_state,events)
 running_before = sorted([s for s in race_state["states"] if s["status"]=="Running"], key=lambda s:(s["position"] if s["position"] else 999,s["total_time"]))
 if not any(state["position"] for state in running_before):
  running_before = sorted(running_before,key=lambda s:s["total_time"])
 pre_lap_times = {s["driver"].name:s["total_time"] for s in race_state["states"] if s["status"]=="Running"}
 lap_data = []
 dnf_this_lap = []
 for state in race_state["states"]:
  if state["status"]!="Running":
   continue
  if state["pit_pending"]:
   _do_pit_stop(state,events)
  start_penalty = _first_lap_grid_penalty(race_state,state) if race_state["lap"]==1 else 0.0
  lap_time,dnf_reason = _simulate_driver_lap(state,race_state["circuit"],race_state["track_wetness"],race_state["safety_car"],start_penalty=start_penalty)
  if dnf_reason:
   state["status"] = dnf_reason
   state["last_lap"] = None
   state["gap"] = None
   state["interval"] = None
   events.append(f"{state['driver'].name} retired: {dnf_reason}")
   dnf_this_lap.append(dnf_reason)
   continue
  lap_data.append({"state":state,"lap_time":lap_time,"projected_total":state["total_time"]+lap_time})
  state["tyre_age"] += 1
  state["warmup_penalty"] = max(0.0, (state.get("warmup_penalty", 0.0) or 0.0) * 0.35 - 0.15)
  state["pit_pending"] = None
 _resolve_on_track_order(running_before,lap_data,events,lap_one=(race_state["lap"]==1))
 red_flag_triggered = _maybe_trigger_red_flag(race_state,dnf_this_lap,pre_lap_times,events)
 if not red_flag_triggered:
  _maybe_deploy_safety_car(race_state,dnf_this_lap,events)
 finished = [s for s in race_state["states"] if s["status"]=="Running"]
 finished.sort(key=lambda s:s["total_time"])
 # The Safety Car slows everyone equally (SAFETY_CAR_LAP_DELTA). On the first
 # lap under SC the existing gaps are kept so a driver can pit before the field
 # bunches; from the second SC lap onward the field is compressed together.
 if race_state["red_flag_stoppage"] or (
  race_state["safety_car"] and race_state.get("safety_car_laps", 0) >= 2
 ):
  _compress_gaps_under_safety_car(finished)
 dnf_occurred = bool(dnf_this_lap)
 for pos,state in enumerate(finished,1):
  state["position"] = pos
  state["gap"] = 0.0 if pos==1 else state["total_time"]-finished[0]["total_time"]
  state["interval"] = 0.0 if pos==1 else state["total_time"]-finished[pos-2]["total_time"]
  state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name,0),pos)
  state["position_delta_reason"] = _describe_position_change(state,state["position_delta"],dnf_occurred)
 retired = [s for s in race_state["states"] if s["status"]!="Running"]
 retired.sort(key=lambda s:s["laps_completed"],reverse=True)
 for idx,state in enumerate(retired,len(finished)+1):
  state["position"] = idx
  state["gap"] = None
  state["interval"] = None
  state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name,0),idx)
  state["position_delta_reason"] = f"Retired: {state['status']}"
 _update_safety_car_timer(race_state,events)
 _annotate_risk_levels(race_state)
 return _snapshot(race_state,events)

def is_race_finished(race_state):
 if race_state["lap"]>=race_state["circuit"].laps:
  return True
 return not any(s["status"]=="Running" for s in race_state["states"])

def final_classification(race_state):
 is_dry_race = not race_state.get("wet_race_declared", False)
 for state in race_state["states"]:
  if state["status"] == "Running" and is_dry_race:
   dry_used = set(state.get("compounds_used", [])) & {"soft", "medium", "hard"}
   if len(dry_used) < 2:
    state["status"] = "DSQ (Tyre Rule)"
 
 ordered = sorted(
  race_state["states"],
  key=lambda s: (
   s["status"] != "Running",
   s["status"] == "DSQ (Tyre Rule)",
   -s["laps_completed"],
   s["total_time"] if s["total_time"] else 10**9
  )
 )
 for pos, s in enumerate(ordered, 1):
  s["position"] = pos
 return ordered

def _create_driver_state(driver,track_wetness):
 init_tyre = initial_tyre(track_wetness)
 return {
  "driver":driver,
  "total_time":0.0,
  "last_lap":None,
  "best_lap":None,
   "tyre":init_tyre,
   "tyre_age":0,
   "warmup_penalty":0.0,
   "compounds_used":[init_tyre],
  "status":"Running",
  "laps_completed":0,
  "position":0,
  "gap":None,
  "interval":None,
  "pit_pending":None,
  "pit_stops":0,
  "position_delta":0,
  "position_delta_reason":"Unchanged",
  "risk_level":"Low",
  "laps_in_traffic":0,
  "_pitted_this_lap":False,
  "_overtook":False,
  "_overtaken":False
 }

def _position_delta(previous_position,current_position):
 if not previous_position or not current_position:
  return 0
 return previous_position-current_position

def _describe_position_change(state,delta,dnf_occurred=False):
 if delta > 0:
  if state.get("_overtook"):
   return "Overtook on track"
  elif state.get("_pitted_this_lap"):
   return "Gained position despite pit stop"
  elif dnf_occurred:
   return "Gained position (retirement ahead)"
  else:
   return f"Gained {delta} position{'s' if delta > 1 else ''}"
 elif delta < 0:
  if state.get("_pitted_this_lap"):
   return "Lost position during pit stop"
  elif state.get("_overtaken"):
   return "Overtaken on track"
  else:
   return f"Lost {abs(delta)} position{'s' if abs(delta) > 1 else ''}"
 else:
  if state.get("_pitted_this_lap"):
   return "Maintained position after pit stop"
  return "Maintained position"

def _annotate_risk_levels(race_state):
 circuit_laps = race_state["circuit"].laps
 wetness = race_state["track_wetness"]
 for state in race_state["states"]:
  if state["status"] != "Running":
   state["risk_level"] = "N/A"
   continue
  driver = state["driver"]
  tyre_name = normalize_tyre(state["tyre"])
  tyre_info = TYRE_RULES.get(tyre_name, TYRE_RULES["medium"])
  wear_multiplier = SAFETY_CAR_WEAR_MULTIPLIER if race_state["safety_car"] else 1.0
  degradation = _tyre_degradation(state["tyre_age"], tyre_info["deg"], _wear_limit(tyre_name), wear_multiplier)
  wet_penalty = _wet_penalty(wetness, tyre_name)
  rel = getattr(driver.team, "reliability", 50)
  tal = getattr(driver, "talent", 80)
  mech, acc, aqua = _dnf_lap_risks(
   rel,
   tal,
   circuit_laps,
   wetness,
   degradation,
   wet_penalty,
   tyre_name,
   tyre_info["dnf"]
  )
  total_risk = mech + acc + aqua
  if total_risk <= RISK_LOW_THRESHOLD:
   state["risk_level"] = "Low"
  elif total_risk <= RISK_MEDIUM_THRESHOLD:
   state["risk_level"] = "Medium"
  else:
   state["risk_level"] = "High"

def _starting_wetness():
 roll = random.randint(1,100)
 if roll<=90:return 0
 if roll<=97:return random.randint(6,30)
 return random.randint(31,100)

def _weather_label(wetness):
 if wetness<=5:return "Dry"
 if wetness<=30:return "Humid"
 if wetness<70:return "Light rain"
 return "Heavy rain"

def _apply_player_commands(race_state,player_commands,events):
 for state in race_state["states"]:
  if state["driver"].team.id!=race_state["player_team"].id or state["status"]!="Running":
   continue
  new_tyre_raw = player_commands.get(state["driver"].name)
  if new_tyre_raw:
   new_tyre = normalize_tyre(new_tyre_raw)
   state["pit_pending"] = new_tyre
   events.append(f"{state['driver'].name} is pitting for {tyre_label(new_tyre)}.")

def _apply_ai_strategy(race_state,events):
 laps_remaining = max(0,race_state["circuit"].laps-race_state["lap"])
 safety_car = race_state["safety_car"]
 personas = race_state["team_personas"]
 running_sorted = sorted([s for s in race_state["states"] if s["status"]=="Running"],key=lambda s:s["total_time"])
 position_index = {s["driver"].name:i for i,s in enumerate(running_sorted)}
 is_dry_race = not race_state.get("wet_race_declared", False)

 for state in race_state["states"]:
  if state["driver"].team.id==race_state["player_team"].id or state["status"]!="Running" or state["pit_pending"]:
   continue
  persona = personas.get(state["driver"].team.id,{"risk_tolerance":1.0,"hesitation":0.25,"stint_bias":0.0})
  tyre = normalize_tyre(state["tyre"])

  # Check mandatory 2-dry-compound rule requirement
  dry_used = set(state.get("compounds_used", [])) & {"soft", "medium", "hard"}
  needs_mandatory_compound = (
   is_dry_race
   and len(dry_used) < 2
   and laps_remaining <= max(8, int(race_state["circuit"].laps * 0.35))
   and state["tyre_age"] >= 4
  )

  # Weather: a tyre that is clearly the wrong choice must be swapped immediately.
  needs_weather_swap = _wet_penalty(race_state["track_wetness"], tyre) >= 1.6
  if needs_weather_swap:
   state["pit_pending"] = _best_tyre_for_conditions(race_state["track_wetness"])
   events.append(f"{state['driver'].name} pits for {tyre_label(state['pit_pending'])} in changing conditions.")
   continue

  if needs_mandatory_compound:
   unused = [t for t in DRY_START if t not in dry_used]
   state["pit_pending"] = unused[0] if unused else _best_tyre_for_conditions(race_state["track_wetness"])
   events.append(f"{state['driver'].name} pits to meet the 2-compound mandatory tyre rule.")
   continue

  idx = position_index.get(state["driver"].name)
  ahead = running_sorted[idx-1] if idx is not None and idx>0 else None
  behind = running_sorted[idx+1] if idx is not None and idx+1<len(running_sorted) else None

  pit_tyre = _choose_pit_tyre(state, race_state, laps_remaining)
  should_pit, reason = _ai_pit_decision(state, race_state, pit_tyre, persona, ahead, behind)
  if not should_pit:
   continue
  if random.random() < persona["hesitation"]:
   continue
  state["pit_pending"] = pit_tyre
  if reason:
   events.append(reason)
  else:
   events.append(f"{state['driver'].name} is pitting for {tyre_label(pit_tyre)}.")

def _ai_pit_decision(state,race_state,pit_tyre,persona=None,ahead=None,behind=None):
 """Decide whether an AI driver should pit this lap.

 Combines tyre cliff detection, tactical undercuts/covers, Safety Car windows and a
 simple expected-total-race-time comparison so teams never pit at a fixed tyre age.
 """
 persona = persona or {"risk_tolerance":1.0,"hesitation":0.25,"stint_bias":0.0}
 risk = persona.get("risk_tolerance", 1.0)
 stint_bias = persona.get("stint_bias", 0.0)
 laps_remaining = max(0, race_state["circuit"].laps - race_state["lap"])
 if laps_remaining <= 2:
  return False, None
 tyre = normalize_tyre(state["tyre"])
 age = state["tyre_age"]
 info = TYRE_RULES.get(tyre, TYRE_RULES["medium"])
 limit = _wear_limit(tyre)
 wear_mult = SAFETY_CAR_WEAR_MULTIPLIER if race_state["safety_car"] else 1.0
 deg_now = _tyre_degradation(age, info["deg"], limit, wear_mult)
 new_info = TYRE_RULES.get(pit_tyre, TYRE_RULES["medium"])

 # Aggressive teams (and positive stint bias) stretch their tyres further.
 cliff = TYRE_CLIFF_DEG * (0.6 + 0.4 * risk) * (1 + 0.15 * stint_bias)

 # Undercut: only with a heavily worn rival ahead, a clearly faster fresh tyre
 # and a clean-air rejoin. Otherwise the advantage is cancelled by traffic.
 undercut = False
 if ahead is not None and not race_state["safety_car"]:
  ahead_tyre = normalize_tyre(ahead.get("tyre", "medium"))
  ahead_info = TYRE_RULES.get(ahead_tyre, TYRE_RULES["medium"])
  ahead_limit = _wear_limit(ahead_tyre)
  ahead_age = ahead.get("tyre_age", 0)
  ahead_deg = _tyre_degradation(ahead_age, ahead_info["deg"], ahead_limit, wear_mult)
  gap = max(0.0, state["total_time"] - ahead["total_time"])
  my_pace = projected_pace(state["driver"], race_state["circuit"], pit_tyre)
  rival_pace = projected_pace(ahead["driver"], race_state["circuit"], ahead_tyre) + ahead_deg
  if (
   gap < UNDERCUT_GAP_THRESHOLD
   and ahead_age >= ahead_limit * UNDERCUT_RIVAL_WEAR_RATIO
   and ahead_deg >= TYRE_CLIFF_DEG * 0.8
   and age >= UNDERCUT_MIN_TYRE_AGE
   and my_pace <= rival_pace - 0.15
   and _predict_rejoin_traffic(state, race_state, pit_tyre) == 0
  ):
   undercut = True

 # Cover: a close rival behind is pitting.
 cover = (
  behind is not None
  and behind.get("pit_pending")
  and max(0.0, behind["total_time"] - state["total_time"]) < COVER_GAP_THRESHOLD
  and age >= COVER_MIN_TYRE_AGE
 )

 pit = False
 reason = None
 if deg_now >= cliff:
  pit = True
  reason = f"{state['driver'].name} pits, {tyre_label(tyre)} tyres are past their best."
 elif undercut:
  pit = True
  reason = f"{state['driver'].name} pits early to try an undercut on {ahead['driver'].name}."
 elif cover:
  pit = True
  reason = f"{state['driver'].name} reacts and covers the pit stop."
 elif race_state["safety_car"] and age >= limit * SC_PIT_MIN_AGE_RATIO:
  # The pack is compressed, so a stop under the Safety Car loses little track
  # position. Only take it when the fresh set is roughly worth it.
  stay = _stint_time_loss(age, info["deg"], limit, laps_remaining, wear_mult)
  fresh = TYRE_WARMUP_COST + _stint_time_loss(0, new_info["deg"], _wear_limit(pit_tyre), laps_remaining, wear_mult)
  pace_delta = (info["pace"] - new_info["pace"]) * laps_remaining
  benefit = stay - fresh - NORMAL_PIT_LOSS + pace_delta
  if benefit > -SC_PIT_LOSS_TOLERANCE * risk:
   pit = True
   reason = f"{state['driver'].name} takes the opportunity to pit under the Safety Car."
 elif deg_now >= TYRE_CLIFF_DEG * 0.6 and laps_remaining > 6:
  # Voluntary strategy stop: only when a fresh set clearly saves time over the rest.
  stay = _stint_time_loss(age, info["deg"], limit, laps_remaining, wear_mult)
  fresh = TYRE_WARMUP_COST + _stint_time_loss(0, new_info["deg"], _wear_limit(pit_tyre), laps_remaining, wear_mult)
  pace_delta = (info["pace"] - new_info["pace"]) * laps_remaining
  benefit = stay - fresh - NORMAL_PIT_LOSS + pace_delta
  if benefit > PIT_GAIN_MARGIN * risk:
   pit = True
   reason = f"{state['driver'].name} pits for a fresh set of {tyre_label(pit_tyre)}."

 if not pit:
  return False, None

 # Occasionally stretch the stint instead of pitting: tyre-saving, an overcut attempt
 # or gambling that a Safety Car arrives (only for non-tactical stops).
 if not undercut and not cover and not race_state["safety_car"]:
  if age >= limit * SC_GAMBLE_WINDOW and random.random() < SC_GAMBLE_CHANCE:
   return False, None
  if deg_now >= cliff and random.random() < HOLD_AT_CLIFF_CHANCE:
   return False, None
 return True, reason

def _choose_pit_tyre(state,race_state,laps_remaining):
 """Pick the compound that minimises estimated total race time.

 Balances compound speed against degradation over the distance left, plus the
 cost of any additional stops the compound would force. The mandatory
 two-compound rule is enforced separately before this is consulted.
 """
 wetness = race_state["track_wetness"]
 if wetness > 30:
  return "wet"
 if wetness > 5:
  return "intermediate"
 best = None
 best_cost = None
 for t in DRY_START:
  info = TYRE_RULES[t]
  limit = _wear_limit(t)
  extra_stops = max(0, -(-laps_remaining // max(1, limit)) - 1)
  loss = (TYRE_WARMUP_COST
          + _stint_time_loss(0, info["deg"], limit, laps_remaining)
          + info["pace"] * laps_remaining
          + extra_stops * NORMAL_PIT_LOSS)
  if best_cost is None or loss < best_cost:
   best_cost = loss
   best = t
 return best

def _predict_rejoin_traffic(state,race_state,new_tyre):
 """Estimate how many cars a driver would rejoin behind after a pit stop.

 Returns the number of slower cars the fresh pace would likely be stuck behind.
 """
 pred_total = state["total_time"] + NORMAL_PIT_LOSS
 my_pace = projected_pace(state["driver"], race_state["circuit"], new_tyre)
 traffic = 0
 for other in race_state["states"]:
  if other is state or other["status"] != "Running":
   continue
  if other.get("pit_pending"):
   continue
  gap = other["total_time"] - pred_total
  if -1.5 < gap < 3.0:
   other_tyre = normalize_tyre(other["tyre"])
   other_pace = projected_pace(other["driver"], race_state["circuit"], other_tyre)
   other_pace += _tyre_degradation(other["tyre_age"], TYRE_RULES[other_tyre]["deg"], _wear_limit(other_tyre), 1.0)
   if other_pace > my_pace - 0.4:
    traffic += 1
 return traffic

def _tyre_degradation(age,deg,wear_limit,wear_multiplier=1.0):
 """Progressive tyre degradation.

 Low in the first laps (green phase), rising smoothly to the cliff at the wear
 limit, then falling off sharply if the driver overextends the stint.
 """
 wl = max(1.0, wear_limit)
 if age <= wl:
  p = age / wl
  return (0.12 * p + 0.30 * p * p + 0.28 * p * p * p * p) * deg * wear_multiplier
 over = age - wl
 return (0.70 + 0.06 * over) * deg * wear_multiplier

def _stint_time_loss(age,deg,wear_limit,laps,wear_multiplier=1.0):
 """Total seconds lost to degradation over the next `laps` laps from `age`."""
 total = 0.0
 for _ in range(max(0, int(laps))):
  total += _tyre_degradation(age, deg, wear_limit, wear_multiplier)
  age += 1
 return total

def _update_weather(race_state,events):
 _evolve_rain_state(race_state,events)
 change = _wetness_delta(race_state["rain_state"],race_state["track_wetness"])
 race_state["track_wetness"] = max(0,min(100,race_state["track_wetness"]+change))
 if race_state["track_wetness"] > 5:
  race_state["wet_race_declared"] = True
 new_weather = _weather_label(race_state["track_wetness"])
 if new_weather!=race_state["weather"]:
  race_state["weather"] = new_weather
  race_state["weather_grace_laps"] = 1
  events.append(f"Weather changed to {new_weather} ({race_state['track_wetness']}% wet).")

def _do_pit_stop(state,events):
 new_tyre = normalize_tyre(state["pit_pending"])
 state["tyre"] = new_tyre
 state["tyre_age"] = 0
 state["warmup_penalty"] = TYRE_WARMUP_PENALTY
 state["pit_stops"] += 1
 state["_pitted_this_lap"] = True
 if "compounds_used" not in state:
  state["compounds_used"] = []
 if new_tyre not in state["compounds_used"]:
  state["compounds_used"].append(new_tyre)
 events.append(f"{state['driver'].name} switched to {tyre_label(new_tyre)} tyres.")

def _simulate_driver_lap(state,circuit,track_wetness,safety_car=False,start_penalty=0.0):
 tyre_key = normalize_tyre(state["tyre"])
 tyre = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
 driver = state["driver"]
 talent = getattr(driver, "talent", 80)
 team = driver.team
 engine = getattr(team, "engine", 50)
 aero = getattr(team, "aerodynamics", 50)
 reliability = getattr(team, "reliability", 50)

 driver_gain = talent * 0.035
 car_gain = (engine * getattr(circuit, "engine_factor", 0.5) + aero * getattr(circuit, "aero_factor", 0.5)) * 0.022
 wear_multiplier = SAFETY_CAR_WEAR_MULTIPLIER if safety_car else 1.0

 # Increased thermal degradation if running wet tyres on dry track
 if track_wetness <= 5 and tyre_key in ("intermediate", "wet"):
  wear_multiplier *= 2.2

 degradation = _tyre_degradation(state["tyre_age"], tyre["deg"], _wear_limit(tyre_key), wear_multiplier)
 global_wet_slowdown = track_wetness * 0.02
 wet_penalty = _wet_penalty(track_wetness, tyre_key)
 noise = random.gauss(0, 0.28)
 pit_loss = NORMAL_PIT_LOSS if (state.get("pit_pending") or state.get("_pitted_this_lap")) else 0.0
 warmup = state.get("warmup_penalty", 0.0) or 0.0
 safety_car_delta = SAFETY_CAR_LAP_DELTA if safety_car else 0.0
 traffic_penalty = min(state.get("laps_in_traffic", 0), TRAFFIC_PENALTY_CAP_LAPS) * TRAFFIC_PENALTY_PER_LAP
 lap_time = circuit.base_lap_time - driver_gain - car_gain + tyre["pace"] + degradation + global_wet_slowdown + wet_penalty + pit_loss + warmup + safety_car_delta + traffic_penalty + noise + start_penalty
 dnf_reason = _lap_dnf_event(reliability, talent, circuit.laps, track_wetness, degradation, wet_penalty, tyre_key, tyre["dnf"])
 if dnf_reason:
  return None, dnf_reason
 return lap_time, None

def _first_lap_grid_penalty(race_state,state):
 """Extra time lost on lap 1 based on grid slot (standing start, dirty air, traffic)."""
 pos = state.get("starting_position") or state.get("position") or 1
 if pos<=1:
  lo,hi = 1.0,1.5
 elif pos<=5:
  lo,hi = 1.5,2.2
 elif pos<=10:
  lo,hi = 2.0,3.0
 elif pos<=15:
  lo,hi = 3.0,4.5
 else:
  lo,hi = 4.5,6.5
 penalty = random.uniform(lo,hi)
 # A fast driver trapped behind a notably slower car ahead loses extra time
 ahead = _driver_ahead_in_grid(race_state,state)
 if ahead is not None and ahead["status"]=="Running":
  circuit = race_state["circuit"]
  my_pace = projected_pace(state["driver"],circuit,"soft")
  ahead_pace = projected_pace(ahead["driver"],circuit,"soft")
  if my_pace < ahead_pace - 0.5:
   penalty += random.uniform(0.4,1.3)
 return penalty

def _driver_ahead_in_grid(race_state,state):
 pos = state.get("starting_position") or state.get("position") or 1
 if pos<=1:
  return None
 target = pos-1
 for s in race_state["states"]:
  if (s.get("starting_position") or s.get("position"))==target:
   return s
 return None

def _wet_penalty(track_wetness,tyre_name):
 tyre_key = normalize_tyre(tyre_name)
 tyre = TYRE_RULES.get(tyre_key, TYRE_RULES["medium"])
 if tyre["wet_low"]<=track_wetness<=tyre["wet_high"]:
  return 0.0
 if track_wetness<tyre["wet_low"]:
  return (tyre["wet_low"]-track_wetness)*0.05
 return (track_wetness-tyre["wet_high"])*0.08

def _snapshot(race_state,events):
 ordered = sorted(race_state["states"],key=lambda s:s["position"])
 return {"lap":race_state["lap"],"laps":race_state["circuit"].laps,"weather":race_state["weather"],"track_wetness":race_state["track_wetness"],"safety_car":race_state["safety_car"],"table":ordered,"events":events}

def _initial_rain_state(wetness):
 if wetness>30:return "heavy"
 if wetness>5:return "light"
 return "dry"

def _evolve_rain_state(race_state,events):
 rain_multiplier = max(0.1,getattr(race_state["circuit"],"rain_chance_multiplier",1.0))
 state = race_state["rain_state"]
 roll = random.random()
 if state=="dry":
  if roll<min(0.95,0.015*rain_multiplier):
   race_state["rain_state"] = "light"
   events.append("It has started drizzling.")
  return
 if state=="light":
  stop_threshold = min(0.95,0.08/rain_multiplier)
  intensify_threshold = stop_threshold+min(0.95,0.04*rain_multiplier)
  if roll<stop_threshold:
   race_state["rain_state"] = "dry"
   events.append("The rain has stopped.")
  elif roll<intensify_threshold:
   race_state["rain_state"] = "heavy"
   events.append("The rain has intensified.")
  return
 ease_threshold = min(0.95,0.10/rain_multiplier)
 if roll<ease_threshold:
  race_state["rain_state"] = "light"
  events.append("The rain has eased.")

def _wetness_delta(rain_state,track_wetness):
 if rain_state=="dry":
  if track_wetness==0:return 0
  return -random.randint(2,6)
 if rain_state=="light":
  if track_wetness<5:return random.randint(1,3)
  return random.randint(-1,3)
 return random.randint(3,8)

def _weather_forecast(circuit, rain_state, track_wetness, horizons=(5,10,20), trials=2000):
 """Monte-Carlo estimate of the chance of rain (track wetness > 5) within the
 next `horizons` laps, using the same rain model as the race simulation."""
 mult = max(0.1, getattr(circuit, "rain_chance_multiplier", 1.0))
 max_lap = max(horizons)
 counts = {h: 0 for h in horizons}
 for _ in range(trials):
  rs = rain_state
  w = track_wetness
  hit_lap = None
  for lap in range(1, max_lap + 1):
   roll = random.random()
   if rs == "dry":
    if roll < min(0.95, 0.015 * mult):
     rs = "light"
   elif rs == "light":
    stop_threshold = min(0.95, 0.08 / mult)
    intensify_threshold = stop_threshold + min(0.95, 0.04 * mult)
    if roll < stop_threshold:
     rs = "dry"
    elif roll < intensify_threshold:
     rs = "heavy"
   else:
    ease_threshold = min(0.95, 0.10 / mult)
    if roll < ease_threshold:
     rs = "light"
   if rs == "dry":
    delta = 0 if w == 0 else -random.randint(2, 6)
   elif rs == "light":
    delta = random.randint(1, 3) if w < 5 else random.randint(-1, 3)
   else:
    delta = random.randint(3, 8)
   w = max(0, min(100, w + delta))
   if w > 5:
    hit_lap = lap
    break
  if hit_lap is None:
   continue
  for h in horizons:
   if hit_lap <= h:
    counts[h] += 1
 return {str(h): int(round(counts[h] / trials * 100)) for h in horizons}

def _dnf_lap_risks(reliability,talent,laps,track_wetness,degradation,wet_penalty,tyre_name,tyre_risk):
 mechanical = _race_to_lap_risk(0.02+(100-reliability)*0.005,max(1,laps))
 accident_base = 0.003+max(0.0,degradation-1.2)*0.003+max(0.0,wet_penalty-0.6)*0.02+tyre_risk*0.004
 accident_skill = max(0.55,1.05-(talent-80)*0.012)
 accident = _race_to_lap_risk(min(0.08,accident_base*accident_skill),max(1,laps))
 aquaplane = _race_to_lap_risk(_aquaplane_race_risk(track_wetness,wet_penalty,tyre_name),max(1,laps))
 return mechanical,accident,aquaplane

def _lap_dnf_event(reliability,talent,laps,track_wetness,degradation,wet_penalty,tyre_name,tyre_risk):
 mechanical,accident,aquaplane = _dnf_lap_risks(reliability,talent,laps,track_wetness,degradation,wet_penalty,tyre_name,tyre_risk)
 roll = random.random()
 if roll<mechanical:
  return "Mechanical failure"
 if roll<mechanical+accident:
  return "Accident"
 if roll<mechanical+accident+aquaplane:
  return "Aquaplaning"
 return None

def _race_to_lap_risk(race_risk,laps):
 return max(0.0,min(0.95,race_risk))/laps

def _aquaplane_race_risk(track_wetness,wet_penalty,tyre_name):
 tyre_key = normalize_tyre(tyre_name)
 if track_wetness<=30:
  return 0.0
 if tyre_key in ("soft","medium","hard"):
  return min(0.16,(track_wetness-30)*0.002+wet_penalty*0.025)
 if tyre_key=="intermediate" and track_wetness>=65:
  return min(0.07,(track_wetness-65)*0.0015+wet_penalty*0.012)
 return 0.0

def _resolve_on_track_order(running_before,lap_data,events,lap_one=False):
 data_by_id = {entry["state"]["driver"].name:entry for entry in lap_data}
 ordered = []
 for state in running_before:
  if state["status"]!="Running":
   continue
  entry = data_by_id.get(state["driver"].name)
  if entry:
   ordered.append(entry)
 for entry in lap_data:
  if entry not in ordered:
   ordered.append(entry)
 if not ordered:
  return
 resolved = [ordered[0]]
 for entry in ordered[1:]:
  front = resolved[-1]
  front_state = front["state"]
  state = entry["state"]
  start_gap = max(0.0,state["total_time"]-front_state["total_time"])
  if front_state.get("_pitted_this_lap"):
   resolved[-1],entry = entry,front
   state["laps_in_traffic"] = 0
   front_state["laps_in_traffic"] = 0
  elif entry["projected_total"]<front["projected_total"] and start_gap<1.0:
   laps_stuck = state.get("laps_in_traffic",0)
   talent = getattr(state["driver"], "talent", 80)
   if _overtake_succeeds(talent,start_gap,laps_stuck,lap_one):
    resolved[-1],entry = entry,front
    events.append(f"{state['driver'].name} passed {front_state['driver'].name}.")
    state["_overtook"] = True
    front_state["_overtaken"] = True
    state["laps_in_traffic"] = 0
    front_state["laps_in_traffic"] = 0
   else:
    entry["projected_total"] = front["projected_total"]+random.uniform(0.12,0.45)
    entry["lap_time"] = entry["projected_total"]-state["total_time"]
    state["laps_in_traffic"] = laps_stuck+1
    if state["laps_in_traffic"] in (3,6,9):
     events.append(f"{state['driver'].name} is stuck in traffic behind {front_state['driver'].name}.")
  else:
   state["laps_in_traffic"] = 0
  resolved.append(entry)
 for entry in resolved:
  state = entry["state"]
  state["total_time"] = entry["projected_total"]
  state["last_lap"] = entry["lap_time"]
  if entry["lap_time"] is not None:
   if state.get("best_lap") is None or entry["lap_time"] < state["best_lap"]:
    state["best_lap"] = entry["lap_time"]
  state["laps_completed"] = state["laps_completed"]+1

def _overtake_succeeds(talent,start_gap,laps_in_traffic=0,lap_one=False):
 traffic_bonus = min(laps_in_traffic,TRAFFIC_OVERTAKE_BONUS_CAP_LAPS)*TRAFFIC_OVERTAKE_BONUS_PER_LAP
 chance = 0.18+max(0,talent-80)*0.012+(1.0-start_gap)*0.08+traffic_bonus
 if lap_one:
  chance += 0.25
 return random.random()<min(0.85,max(0.12,chance))

def _best_tyre_for_conditions(track_wetness):
 if track_wetness>30:return "wet"
 if track_wetness>5:return "intermediate"
 if track_wetness<=2:return "soft"
 if track_wetness<=4:return "medium"
 return "hard"

def _wear_limit(tyre_name):
 tyre_key = normalize_tyre(tyre_name)
 return {"soft":14,"medium":20,"hard":26,"intermediate":18,"wet":20}.get(tyre_key, 16)

def _maybe_deploy_safety_car(race_state,dnf_reasons,events):
 if race_state["safety_car"]:
  return
 triggers = [r for r in dnf_reasons if r in ("Accident","Aquaplaning")]
 if not triggers:
  return
 chance = 0.6 if "Accident" in triggers else 0.4
 if random.random()<chance:
  race_state["safety_car"] = True
  race_state["safety_car_timer"] = random.randint(3,6)
  race_state["safety_car_laps"] = 0
  events.append("Safety Car deployed.")

def _update_safety_car_timer(race_state,events):
 if not race_state["safety_car"]:
  return
 race_state["safety_car_timer"] -= 1
 if race_state["safety_car_timer"]<=0:
  race_state["safety_car"] = False
  race_state["safety_car_timer"] = 0
  events.append("Safety Car in. Green Flag.")

def _compress_gaps_under_safety_car(finished):
 if not finished:
  return
 base = finished[0]["total_time"]
 for idx,state in enumerate(finished):
  state["total_time"] = base+idx*SAFETY_CAR_GAP_STEP

def _maybe_trigger_red_flag(race_state,dnf_reasons,pre_lap_times,events):
 if race_state["red_flag_stoppage"]:
  return False
 accidents = dnf_reasons.count("Accident")
 if accidents>=2:
  triggered = True
 elif accidents==1:
  triggered = random.random()<0.12
 else:
  triggered = False
 if not triggered:
  return False
 race_state["red_flag_stoppage"] = True
 race_state["safety_car"] = False
 race_state["safety_car_timer"] = 0
 events.append("Red Flag: race suspended following a serious incident.")
 for state in race_state["states"]:
  if state["status"]!="Running":
   continue
  prev_total = pre_lap_times.get(state["driver"].name)
  if prev_total is not None:
   state["total_time"] = prev_total
  state["last_lap"] = None
  state["laps_in_traffic"] = 0
  if state["laps_completed"]>0:
   state["laps_completed"] -= 1
 return True

def _run_red_flag_stoppage_lap(race_state,player_commands):
 events = []
 race_state["lap"] += 1
 previous_positions = {s["driver"].name:s.get("position",0) for s in race_state["states"]}
 _apply_player_commands(race_state,player_commands,events)
 for state in race_state["states"]:
  if state["driver"].team.id==race_state["player_team"].id or state["status"]!="Running" or state["pit_pending"]:
   continue
  suggested = _best_tyre_for_conditions(race_state["track_wetness"])
  if suggested!=normalize_tyre(state["tyre"]):
   state["pit_pending"] = suggested
 for state in race_state["states"]:
  if state["status"]=="Running" and state["pit_pending"]:
   _do_pit_stop(state,events)
   state["pit_pending"] = None
   state["last_lap"] = None
 finished = [s for s in race_state["states"] if s["status"]=="Running"]
 finished.sort(key=lambda s:s["total_time"])
 _compress_gaps_under_safety_car(finished)
 for state in finished:
  state["laps_completed"] += 1
 for pos,state in enumerate(finished,1):
  state["position"] = pos
  state["gap"] = 0.0 if pos==1 else state["total_time"]-finished[0]["total_time"]
  state["interval"] = 0.0 if pos==1 else state["total_time"]-finished[pos-2]["total_time"]
  state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name,0),pos)
  state["position_delta_reason"] = _describe_position_change(state,state["position_delta"])
 retired = [s for s in race_state["states"] if s["status"]!="Running"]
 retired.sort(key=lambda s:s["laps_completed"],reverse=True)
 for idx,state in enumerate(retired,len(finished)+1):
  state["position"] = idx
  state["gap"] = None
  state["interval"] = None
  state["position_delta"] = _position_delta(previous_positions.get(state["driver"].name,0),idx)
  state["position_delta_reason"] = f"Retired: {state['status']}"
 race_state["red_flag_stoppage"] = False
 race_state["safety_car"] = True
 race_state["safety_car_timer"] = random.randint(2,4)
 events.append("Race resumes behind the Safety Car.")
 return _snapshot(race_state,events)