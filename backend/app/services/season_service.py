from typing import Dict, List, Optional


class SeasonService:
    """Owns championship-level state: standings, season results and circuit order."""

    PTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

    def __init__(self, drivers, circuits, teams) -> None:
        self.drivers = drivers
        self.circuits = circuits
        self.teams = teams
        self.player_team = None
        self._circuit_index = 0
        self._standings: Dict[str, int] = {d.name: 0 for d in drivers}
        self._constructor_standings: Dict[str, int] = {t.get("name"): 0 for t in teams.values()}
        self._season_results: List[dict] = []
        self._season_finished = False

    # --- data helpers -------------------------------------------------------
    def list_teams(self) -> List[dict]:
        """Return teams with aggregated info including drivers list."""
        by_team = {}
        for d in self.drivers:
            tid = getattr(d.team, "id", None)
            by_team.setdefault(tid, []).append({"name": d.name, "talent": d.talent, "country": getattr(d, "country", "")})

        result = []
        for tid, t in self.teams.items():
            result.append(
                {
                    "id": tid,
                    "name": t.get("name"),
                    "engine": t.get("engine"),
                    "aerodynamics": t.get("aerodynamics"),
                    "reliability": t.get("reliability"),
                    "logo": t.get("logo", ""),
                    "color_primary": t.get("color_primary", "#1F2937"),
                    "color_secondary": t.get("color_secondary", "#374151"),
                    "drivers_colors": t.get("drivers_colors", {}),
                    "drivers": by_team.get(tid, []),
                }
            )
        return result

    def team_object(self, team_id: int):
        """Find the Team object instance among the drivers' team references."""
        for d in self.drivers:
            if getattr(d.team, "id", None) == team_id:
                return d.team
        return None

    # --- season lifecycle ---------------------------------------------------
    def reset(self) -> None:
        self._circuit_index = 0
        self._standings = {d.name: 0 for d in self.drivers}
        self._constructor_standings = {t.get("name"): 0 for t in self.teams.values()}
        self._season_results = []
        self._season_finished = False

    def award_points(self, classification) -> None:
        pos = 0
        for state in classification:
            if state["status"] == "Running":
                if pos < len(self.PTS):
                    points = self.PTS[pos]
                    self._standings[state["driver"].name] += points
                    self._constructor_standings[state["driver"].team.name] = self._constructor_standings.get(state["driver"].team.name, 0) + points
            pos += 1

    def add_result(self, summary: dict) -> None:
        self._season_results.append(summary)

    def advance_circuit(self) -> bool:
        """Move to the next circuit. Returns True when the season is complete."""
        self._circuit_index += 1
        if self._circuit_index >= len(self.circuits):
            self._season_finished = True
            return True
        return False

    def current_circuit(self):
        return self.circuits[self._circuit_index]

    # --- queries -------------------------------------------------------------
    def get_standings(self) -> List[dict]:
        items = sorted(self._standings.items(), key=lambda x: x[1], reverse=True)
        teams_by_driver = {d.name: d.team.name for d in self.drivers}
        return [{"driver": k, "team": teams_by_driver.get(k, ""), "points": v} for k, v in items]

    def get_constructor_standings(self) -> List[dict]:
        items = sorted(self._constructor_standings.items(), key=lambda x: x[1], reverse=True)
        return [{"team": k, "points": v} for k, v in items]

    @property
    def circuit_index(self) -> int:
        return self._circuit_index

    @property
    def season_results(self) -> List[dict]:
        return self._season_results

    @property
    def season_finished(self) -> bool:
        return self._season_finished
