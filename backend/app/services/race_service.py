from typing import Dict, List, Optional
import json
from pathlib import Path
import copy

from simulation.race import (
    create_race,
    is_race_finished,
    run_lap,
    final_classification,
    _weather_forecast,
    _initial_rain_state,
)
from simulation.qualifying import (
    create_qualifying,
    advance_qualifying,
    skip_qualifying,
    qualifying_snapshot,
    grid_names,
)
from utils import load

from backend.app.schemas.race_state import DriverState, RaceEvent, RaceState


class RaceService:
    def __init__(self) -> None:
        # Load data from the shared utils loader (drivers, circuits)
        self.drivers, self.circuits = load()
        if not self.circuits:
            raise RuntimeError("No circuits available")
        if not self.drivers:
            raise RuntimeError("No drivers available")

        # Teams are stored in data/static/teams.json — load here for the team selection UI
        teams_path = Path("data/static/teams.json")
        teams_json = json.loads(teams_path.read_text())
        # Map id -> Team-like dict
        self.teams = {t["id"]: t for t in teams_json}

        # Player team will be set when the user starts a season
        self.player_team = None

        # Race is not created until player selects a team and starts a season
        self.race = None

        # current circuit index for championship mode
        self._circuit_index = 0

        # championship standings (driver name -> points)
        self._standings: Dict[str, int] = {d.name: 0 for d in self.drivers}
        self._constructor_standings: Dict[str, int] = {t.get("name"): 0 for t in self.teams.values()}

        # store completed race results
        self._season_results: List[dict] = []

        # season finished flag
        self._season_finished = False

        # Keep the last snapshot returned by the engine for event reporting
        self._last_snapshot = None

        # history: list of snapshots per lap for analytics
        self._history: List[dict] = []

        # flag to avoid double finalization
        self._race_finalized = False

        # Weekend phase machine: selection -> qualifying -> tyre_selection -> race
        self.phase = "selection"
        self._qualifying = None
        self._grid = None
        self._starting_tyres: Dict[str, str] = {}
        self._weekend_wetness = 0
        self._weekend_weather = ""

    # Team related helpers -------------------------------------------------
    def list_teams(self) -> List[dict]:
        """Return teams with aggregated info including drivers list."""
        # group drivers by team id
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

    def start_season(self, team_id: int):
        """Initialize a race using the provided player team id.

        This does not advance the race; it only creates the race instance.
        """
        if team_id not in self.teams:
            raise ValueError("Invalid team id")

        # Find Team object instance among drivers' team references
        team_obj = None
        for d in self.drivers:
            if getattr(d.team, "id", None) == team_id:
                team_obj = d.team
                break
        if team_obj is None:
            # Fallback: construct a minimal team-like object from JSON
            t = self.teams[team_id]
            class _T:
                pass

            team_obj = _T()
            team_obj.id = t["id"]
            team_obj.name = t["name"]
            team_obj.engine = t.get("engine", 50)
            team_obj.aerodynamics = t.get("aerodynamics", 50)
            team_obj.reliability = t.get("reliability", 50)

        self.player_team = team_obj
        # Initialize championship state
        self._circuit_index = 0
        self._standings = {d.name: 0 for d in self.drivers}
        self._constructor_standings = {t.get("name"): 0 for t in self.teams.values()}
        self._season_results = []
        self._season_finished = False
        self._history = []
        self._race_finalized = False

        # Start the first weekend: qualifying first, then the race from its grid
        self._start_weekend()

    def _start_weekend(self) -> None:
        """Begin a new race weekend with a qualifying session."""
        self.race = None
        self._last_snapshot = None
        self._history = []
        self._race_finalized = False
        self._starting_tyres = {}
        self._grid = None
        self._qualifying = create_qualifying(self.drivers, self.circuits[self._circuit_index])
        self._weekend_wetness = self._qualifying["track_wetness"]
        self._weekend_weather = self._qualifying["weather"]
        self.phase = "qualifying"

    # Game interaction -----------------------------------------------------
    def qualifying_tick(self, seconds: int = 10) -> RaceState:
        """Advance the current qualifying session by `seconds` of simulated track time."""
        if self.phase != "qualifying" or self._qualifying is None:
            return self.get_state()
        _, events = advance_qualifying(self._qualifying, max(1, seconds))
        if events:
            self._qualifying["events"].extend(events)
        if self._qualifying["finished"]:
            self._finalize_qualifying()
        return self.get_state()

    def qualifying_skip(self, phase: Optional[str] = None) -> RaceState:
        """Fast-forward qualifying until the requested phase (Q2/Q3) starts, or
        until the full grid is set when no phase is given."""
        if self.phase != "qualifying" or self._qualifying is None:
            return self.get_state()
        _, events = skip_qualifying(self._qualifying, phase)
        if events:
            self._qualifying["events"].extend(events)
        if self._qualifying["finished"]:
            self._finalize_qualifying()
        return self.get_state()

    def _finalize_qualifying(self) -> None:
        if self._qualifying is None:
            return
        self._grid = grid_names(self._qualifying)
        self.phase = "tyre_selection"

    def start_race(self, starting_tyres: Optional[Dict[str, str]] = None) -> RaceState:
        """Build the race from the qualifying grid and the player's chosen starting tyres."""
        if self.phase != "tyre_selection" or not self._grid:
            return self.get_state()
        self._starting_tyres = {str(k): v for k, v in (starting_tyres or {}).items()}
        self.race = create_race(
            self.drivers,
            self.circuits[self._circuit_index],
            self.player_team,
            grid=self._grid,
            starting_tyres=self._starting_tyres,
            track_wetness=self._weekend_wetness,
        )
        self._last_snapshot = None
        self._history = []
        self._race_finalized = False
        self.phase = "race"
        return self.get_state()

    def _build_qualifying_state(self) -> RaceState:
        circuit = self.circuits[self._circuit_index]
        wetness = self._qualifying["track_wetness"]
        return RaceState(
            race_name=circuit.name,
            lap=0,
            total_laps=0,
            weather=self._qualifying["weather"],
            weather_forecast=_weather_forecast(circuit, _initial_rain_state(wetness), wetness),
            finished=False,
            phase="qualifying",
            qualifying=qualifying_snapshot(self._qualifying),
            player_team_id=self._player_team_id(),
            classification=[],
            events=[],
        )

    def _build_tyre_selection_state(self) -> RaceState:
        circuit = self.circuits[self._circuit_index]
        wetness = self._qualifying["track_wetness"]
        return RaceState(
            race_name=circuit.name,
            lap=0,
            total_laps=0,
            weather=self._weekend_weather,
            weather_forecast=_weather_forecast(circuit, _initial_rain_state(wetness), wetness),
            finished=False,
            phase="tyre_selection",
            grid=self._grid_rows(),
            starting_tyres=self._starting_tyres,
            player_team_id=self._player_team_id(),
            classification=[],
            events=[],
        )

    def _player_team_id(self) -> Optional[int]:
        return self.player_team.id if self.player_team is not None else None

    def _grid_rows(self) -> List[dict]:
        if self._qualifying is None:
            return []
        rows = []
        for entry in sorted(self._qualifying["entries"].values(), key=lambda e: e["grid_position"] or 999):
            if entry["grid_position"] is None:
                continue
            best = entry["phase_bests"].get("Q3") or entry["phase_bests"].get("Q2") or entry["phase_bests"].get("Q1")
            rows.append(
                {
                    "position": entry["grid_position"],
                    "driver": entry["driver"].name,
                    "team": entry["team"],
                    "best_lap": best,
                    "eliminated": entry["eliminated"],
                }
            )
        return rows

    def get_state(self) -> RaceState:
        """Return the current state depending on the weekend phase.

        If a season hasn't been started yet, returns an empty RaceState
        (finished=True, phase="selection") so the frontend can show team
        selection.
        """
        if self.phase == "qualifying" and self._qualifying is not None:
            return self._build_qualifying_state()
        if self.phase == "tyre_selection":
            return self._build_tyre_selection_state()
        if self.race is None:
            return RaceState(
                race_name="",
                lap=0,
                total_laps=0,
                weather="",
                strategy_locked=False,
                finished=True,
                phase=self.phase or "selection",
                player_team_id=self._player_team_id(),
                classification=[],
                events=[],
            )

        # If race has finished, prefer the final classification from the engine
        finished = is_race_finished(self.race)

        if finished:
            # ensure points and season summary are finalized before exposing state
            if not self._race_finalized:
                self._finalize_race()
                self._race_finalized = True

            table_source = final_classification(self.race)
            events = self._last_snapshot["events"] if self._last_snapshot else []
            lap = self.race.get("lap", 0)
            laps = self.race["circuit"].laps
            weather = self.race.get("weather", "")
            snapshot = {
                "lap": lap,
                "laps": laps,
                "weather": weather,
                "table": table_source,
                "events": events,
            }
            return self._build_state(snapshot)

        # Build a snapshot-like structure from current race state without advancing
        ordered = sorted(
            self.race["states"],
            key=lambda s: (s["position"] if s.get("position") else 999, s.get("total_time", 0.0)),
        )
        snapshot = {
            "lap": self.race.get("lap", 0),
            "laps": self.race["circuit"].laps,
            "weather": self.race.get("weather", ""),
            "table": ordered,
            "events": self._last_snapshot.get("events", []) if self._last_snapshot else [],
        }
        return self._build_state(snapshot)

    def next_lap(self, commands: Optional[Dict[str, str]] = None) -> RaceState:
        """Advance the race by one lap using optional pit commands for player drivers.

        commands: mapping driver_name -> tyre_name
        """
        if self.race is None:
            # No race started yet
            return self.get_state()

        if is_race_finished(self.race):
            # No further advancement once finished
            return self.get_state()

        cmds = commands or {}
        snapshot = run_lap(self.race, cmds)
        self._last_snapshot = snapshot

        # record history for analytics — store a deep copy so past snapshots don't mutate
        self._history.append(copy.deepcopy(snapshot))

        # If the race finishes as a result of this lap, ensure final classification is used
        if is_race_finished(self.race):
            # final_classification returns ordered list of states
            final_table = final_classification(self.race)
            snapshot = {
                "lap": self.race.get("lap", 0),
                "laps": self.race["circuit"].laps,
                "weather": self.race.get("weather", ""),
                "table": final_table,
                "events": snapshot.get("events", []),
            }
            # finalize race once: award points and store summary for standings
            if not self._race_finalized:
                self._finalize_race()
                self._race_finalized = True

        return self._build_state(snapshot)

    def _finalize_race(self):
        """Award points and store race summary without advancing.

        Idempotent: calling multiple times will not double-award points or duplicate the summary.
        """
        if self.race is None:
            return
        if self._race_finalized:
            return

        # Award points based on final classification
        PTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
        classification = final_classification(self.race)
        pos = 0
        for state in classification:
            if state["status"] == "Running":
                if pos < len(PTS):
                    points = PTS[pos]
                    self._standings[state["driver"].name] += points
                    self._constructor_standings[state["driver"].team.name] = self._constructor_standings.get(state["driver"].team.name, 0) + points
            pos += 1

        race_summary = {
            "circuit": self.race["circuit"].name,
            "lap": self.race.get("lap", 0),
            "classification": [
                {
                    "position": s.get("position"),
                    "driver": s["driver"].name,
                    "team": s["driver"].team.name,
                    "gap": s.get("gap"),
                    "status": s.get("status"),
                    "pit_stops": s.get("pit_stops", 0),
                }
                for s in classification
            ],
            "events": self._last_snapshot.get("events", []) if self._last_snapshot else [],
            "history": list(self._history),
        }
        self._season_results.append(race_summary)
        # mark finalized so subsequent calls are no-ops
        self._race_finalized = True

    def continue_to_next_race(self) -> RaceState:
        """Advance to next circuit. Ensures current race is finalized (points & summary stored)
        before moving on. Returns next race state or final season summary if season finished.
        """
        if self.race is None:
            raise RuntimeError("No race in progress")

        if not is_race_finished(self.race):
            raise RuntimeError("Race not finished yet")

        # Ensure finalization (idempotent) so standings and season results are ready
        if not self._race_finalized:
            self._finalize_race()

        # advance circuit index
        self._circuit_index += 1
        if self._circuit_index >= len(self.circuits):
            # season finished
            self._season_finished = True
            self.phase = "season_finished"
            return self.get_state()

        # start the next weekend (qualifying first)
        self._start_weekend()
        return self.get_state()

    def get_standings(self) -> List[dict]:
        """Return championship standings sorted by points."""
        items = sorted(self._standings.items(), key=lambda x: x[1], reverse=True)
        teams_by_driver = {d.name: d.team.name for d in self.drivers}
        return [{"driver": k, "team": teams_by_driver.get(k, ""), "points": v} for k, v in items]

    def get_constructor_standings(self) -> List[dict]:
        """Return constructor standings sorted by points."""
        items = sorted(self._constructor_standings.items(), key=lambda x: x[1], reverse=True)
        return [{"team": k, "points": v} for k, v in items]

    def analytics(self) -> dict:
        """Return analytics data computed from lap history.

        lap history is a list of snapshots recorded after each lap.
        """
        # Build per-driver lap list
        per_driver = {d.name: [] for d in self.drivers}
        for snap in self._history:
            lap = snap.get("lap", 0)
            for state in snap.get("table", []):
                dname = state["driver"].name
                per_driver[dname].append(
                    {
                        "lap": lap,
                        "lap_time": state.get("last_lap"),
                        "tyre": state.get("tyre"),
                        "tyre_age": state.get("tyre_age"),
                        "position": state.get("position"),
                        "gap": state.get("gap"),
                        "gap_to_leader": state.get("gap"),
                        "interval": state.get("interval"),
                        "pit_stops": state.get("pit_stops", 0),
                        "status": state.get("status"),
                        "team": state["driver"].team.name,
                    }
                )

        # Tyre stints and basic stats per driver
        stints = {}
        for name, laps in per_driver.items():
            stints[name] = []
            if not laps:
                continue
            current = None
            start = None
            for entry in laps:
                if current is None:
                    current = entry["tyre"]
                    start = entry["lap"]
                    length = 1
                else:
                    if entry["tyre"] == current:
                        length = entry["lap"] - start + 1
                    else:
                        stints[name].append({"tyre": current, "start": start, "end": entry["lap"] - 1})
                        current = entry["tyre"]
                        start = entry["lap"]
            if current is not None:
                stints[name].append({"tyre": current, "start": start, "end": laps[-1]["lap"]})

        # Identify laps where Safety Car was active
        sc_laps = [snap.get("lap") for snap in self._history if snap.get("safety_car")]

        return {"per_driver": per_driver, "stints": stints, "sc_laps": sc_laps}

    def export_csv(self) -> str:
        """Export lap telemetry as CSV."""
        import io, csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["driver", "lap", "lap_time", "tyre", "tyre_age", "position", "gap", "interval", "pit_stops", "status"])
        for snap in self._history:
            lap = snap.get("lap", 0)
            for state in snap.get("table", []):
                writer.writerow([
                    state["driver"].name,
                    lap,
                    state.get("last_lap"),
                    state.get("tyre"),
                    state.get("tyre_age"),
                    state.get("position"),
                    state.get("gap"),
                    state.get("interval"),
                    state.get("pit_stops", 0),
                    state.get("status"),
                ])
        return output.getvalue()

    def _build_state(self, snapshot: dict) -> RaceState:
        classification: List[DriverState] = []

        for state in snapshot["table"]:
            # state["driver"] is a Driver dataclass instance
            driver = state["driver"]
            classification.append(
                DriverState(
                    position=state.get("position", 0),
                    driver=driver.name,
                    team=driver.team.name,
                    tyre=state.get("tyre", ""),
                    tyre_age=state.get("tyre_age", 0),
                    gap=state.get("gap"),
                    last_lap=0.0 if state.get("last_lap") is None else state.get("last_lap"),
                    best_lap=0.0 if state.get("best_lap") is None else state.get("best_lap"),
                    status=state.get("status", ""),
                    position_delta=state.get("position_delta", 0),
                    position_delta_reason=state.get("position_delta_reason", "Unchanged"),
                    risk_level=state.get("risk_level", "Low"),
                    pit_stops=state.get("pit_stops", 0),
                )
            )

        events = [
            RaceEvent(lap=snapshot.get("lap", 0), message=event) for event in snapshot.get("events", [])
        ]

        finished = is_race_finished(self.race)
        sc = self.race.get("safety_car", False) if self.race else snapshot.get("safety_car", False)
        rf = self.race.get("red_flag_stoppage", False) if self.race else snapshot.get("red_flag", False)

        return RaceState(
            race_name=self.race["circuit"].name,
            lap=snapshot.get("lap", 0),
            total_laps=snapshot.get("laps", self.race["circuit"].laps),
            weather=snapshot.get("weather", ""),
            weather_forecast=_weather_forecast(self.race["circuit"], self.race["rain_state"], self.race["track_wetness"]),
            safety_car=sc,
            red_flag=rf,
            finished=finished,
            phase=self.phase,
            grid=self._grid,
            starting_tyres=self._starting_tyres,
            player_team_id=self._player_team_id(),
            classification=classification,
            events=events,
        )


# Singleton used by the FastAPI router
race_service = RaceService()
