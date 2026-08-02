from utils import load
from simulation.race import create_race,run_lap,is_race_finished,final_classification

PTS=[25,18,15,12,10,8,6,4,2,1]
TYRES=("macio","medio","duro","intermediario","chuva")

class Season:
 def __init__(self,player_team):
  self.drivers,self.circuits=load();self.i=0;self.player_team=player_team;self.points={d.name:0 for d in self.drivers}
 def has_next(self):return self.i<len(self.circuits)
 def race(self):return self.circuits[self.i]
 def run(self):
  c=self.race();race=create_race(self.drivers,c,self.player_team)
  print(f"\n=== {c.name} ===")
  print(f"Selected team: {self.player_team.name}")
  while not is_race_finished(race):
   self._show_snapshot(run_lap(race,self._collect_commands(race)))
   if not is_race_finished(race):input("\nENTER for next lap...")
  self._finish_race(final_classification(race))
  self.i+=1
 def _collect_commands(self,race):
  print(f"\nLap {race['lap']+1}/{race['circuit'].laps} | Weather: {race['weather']} | Track wetness: {race['track_wetness']}%")
  print("Pit commands for your team: press ENTER to keep current tyre, or type a tyre to change")
  cmds={}
  for state in race["states"]:
   if state["driver"].team.id!=self.player_team.id or state["status"]!="Running":
    continue
   ans=input(f"{state['driver'].name} ({state['tyre']} wear {state['tyre_age']}): ").strip().lower()
   if ans in TYRES:cmds[state["driver"].name]=ans
  return cmds
 def _show_snapshot(self,snap):
  print(f"\n--- Lap {snap['lap']}/{snap['laps']} | {snap['weather']} | Wet {snap['track_wetness']}% ---")
  print("POS DRIVER               TEAM            TOTAL/LEADER    LAST LAP   GAP AHEAD TYRE          STOPS")
  for event in snap["events"]:print(f"* {event}")
  for state in snap["table"]:
   last_lap=self._format_lap_time(state["last_lap"])
   total="Leader" if state["gap"]==0 else (f"+{state['gap']:.3f}s" if state["gap"] is not None else state["status"])
   interval="Leader" if state["interval"]==0 else (f"+{state['interval']:.3f}s" if state["interval"] is not None else "-")
   tyre_text=f"{state['tyre']} d{state['tyre_age']}"
   print(f"{state['position']:2}. {state['driver'].name:20} {state['driver'].team.name:15} {total:14} {last_lap:10} {interval:10} {tyre_text:13} {state['pit_stops']:2}")
 def _finish_race(self,classification):
  print("\nFINAL RESULT")
  points_pos=0
  for state in classification:
   if state["status"]=="Running":
    if points_pos<10:self.points[state["driver"].name]+=PTS[points_pos]
   points_pos+=1
   total="Leader" if state["gap"]==0 else (f"+{state['gap']:.3f}s" if state["gap"] is not None else state["status"])
   print(f"{state['position']:2}. {state['driver'].name:20} {state['driver'].team.name:15} {total} | pits {state['pit_stops']}")
  print("\nCHAMPIONSHIP STANDINGS")
  for i,(n,p) in enumerate(sorted(self.points.items(),key=lambda x:x[1],reverse=True),1):print(f"{i:2}. {n:20} {p}")
 def _format_lap_time(self,lap_time):
  if lap_time is None:return "-"
  minutes=int(lap_time//60)
  seconds=lap_time-minutes*60
  return f"{minutes}:{seconds:06.3f}"
