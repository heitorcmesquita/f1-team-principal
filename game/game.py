from game.season import Season
from utils import load
class Game:
 def __init__(self):
  self.drivers,self.circuits=load()
  self.player_team=self._choose_team()
  self.s=Season(self.player_team)
 def play(self):
  while self.s.has_next():
   input(f"\nProxima corrida: {self.s.race().name} (ENTER)")
   self.s.run()
 def _choose_team(self):
  teams=[]
  seen=set()
  for driver in self.drivers:
   if driver.team.id not in seen:
    teams.append(driver.team);seen.add(driver.team.id)
  print("Escolha sua equipe:")
  for i,team in enumerate(teams,1):print(f"{i:2}. {team.name}")
  while True:
   choice=input("Numero da equipe: ").strip()
   if choice.isdigit() and 1<=int(choice)<=len(teams):return teams[int(choice)-1]
   print("Escolha invalida.")
