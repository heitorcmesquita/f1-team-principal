from typing import Dict, List, Optional
import json
import random
from datetime import datetime
from pathlib import Path

from simulation.race import (
    create_race,
    is_race_finished,
    run_lap,
    final_classification,
    weather_forecast,
    initial_rain_state,
)
from simulation.qualifying import (
    create_qualifying,
    advance_qualifying,
    skip_qualifying,
    qualifying_snapshot,
    grid_names,
)
from utils import load

from backend.app.schemas.race_state import RaceEvent, RaceState
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.save_service import (
    SAVE_PATH,
    _from_jsonable,
    _to_jsonable,
    build_lookup,
    minimal_qualifying,
)
from backend.app.services.season_service import SeasonService
from backend.app.services.state_builder import build_classification, build_driver_state

# Keep the event feed from growing forever across a long season.
MAX_EVENTS = 200


class RaceService:
    """Weekend + race orchestration.

    Composes a SeasonService (standings, results, circuit order) and an
    AnalyticsService (lap history) while owning the weekend phase machine:
    selection -> qualifying -> tyre_selection -> race.
    """

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
        self.teams = {t["id"]: t for t in teams_json}

        # Season + analytics are delegated to dedicated services
        self.season = SeasonService(self.drivers, self.circuits, self.teams)
        self.analytics_svc = AnalyticsService(self.drivers)

        # Player team will be set when the user starts a season
        self.player_team = None

        # Race is not created until player selects a team and starts a season
        self.race = None

        # Weekend phase machine: selection -> qualifying -> tyre_selection -> race
        self.phase = "selection"
        self._qualifying = None
        self._grid = None
        self._starting_tyres: Dict[str, str] = {}
        self._weekend_wetness = 0
        self._weekend_weather = ""

        # Keep the last snapshot returned by the engine for event reporting
        self._last_snapshot = None

        # Accumulated (lap, message) events across the current race
        self._race_events: List[tuple] = []

        # weather forecast cache keyed by (circuit, rain_state, wetness)
        self._forecast_cache: Dict[tuple, dict] = {}

        # flag to avoid double finalization
        self._race_finalized = False

    def reset(self) -> None:
        """Return the service to a fresh pre-season state (team selection).

        Used so a new visitor (who has no browser save) does not inherit the
        game world of a previous visitor on the shared server.
        """
        self.season.reset()
        self.player_team = None
        self.season.player_team = None
        self.race = None
        self.phase = "selection"
        self._qualifying = None
        self._grid = None
        self._starting_tyres = {}
        self._weekend_wetness = 0
        self._weekend_weather = ""
        self._last_snapshot = None
        self._race_events = []
        self._forecast_cache = {}
        self._race_finalized = False
        self.analytics_svc._history = []

    # Team related helpers -------------------------------------------------
    def list_teams(self) -> List[dict]:
        return self.season.list_teams()

    def start_season(self, team_id: int):
        """Initialize a race using the provided player team id.

        This does not advance the race; it only creates the race instance.
        """
        if team_id not in self.teams:
            raise ValueError("Invalid team id")

        # Find Team object instance among drivers' team references
        team_obj = self.season.team_object(team_id)
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
        self.season.player_team = team_obj
        # Initialize championship state
        self.season.reset()

        # Start the first weekend: qualifying first, then the race from its grid
        self._start_weekend()

    def _start_weekend(self) -> None:
        """Begin a new race weekend with a qualifying session."""
        self.race = None
        self._last_snapshot = None
        self._race_events = []
        self._forecast_cache = {}
        self._race_finalized = False
        self._starting_tyres = {}
        self._grid = None
        self.analytics_svc.reset()
        self._qualifying = create_qualifying(self.drivers, self.season.current_circuit())
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
            self.season.current_circuit(),
            self.player_team,
            grid=self._grid,
            starting_tyres=self._starting_tyres,
            track_wetness=self._weekend_wetness,
        )
        self._last_snapshot = None
        self._race_events = []
        self._race_finalized = False
        self.phase = "race"
        return self.get_state()

    def _build_qualifying_state(self) -> RaceState:
        circuit = self.season.current_circuit()
        wetness = self._qualifying["track_wetness"]
        return RaceState(
            race_name=circuit.name,
            lap=0,
            total_laps=0,
            weather=self._qualifying["weather"],
            weather_forecast=self._forecast(circuit, initial_rain_state(wetness), wetness),
            finished=False,
            phase="qualifying",
            season_finished=self.season.season_finished,
            qualifying=qualifying_snapshot(self._qualifying),
            player_team_id=self._player_team_id(),
            classification=[],
            events=[],
            **self._season_context(),
        )

    def _build_tyre_selection_state(self) -> RaceState:
        circuit = self.season.current_circuit()
        wetness = self._qualifying["track_wetness"]
        return RaceState(
            race_name=circuit.name,
            lap=0,
            total_laps=0,
            weather=self._weekend_weather,
            weather_forecast=self._forecast(circuit, initial_rain_state(wetness), wetness),
            finished=False,
            phase="tyre_selection",
            season_finished=self.season.season_finished,
            grid=self._grid_rows(),
            starting_tyres=self._starting_tyres,
            player_team_id=self._player_team_id(),
            classification=[],
            events=[],
            **self._season_context(),
        )

    def _player_team_id(self) -> Optional[int]:
        return self.player_team.id if self.player_team is not None else None

    def _season_context(self) -> dict:
        return {
            "circuit_index": self.season.circuit_index,
            "total_circuits": len(self.season.circuits),
        }

    def _forecast(self, circuit, rain_state, wetness) -> dict:
        """Cached rain-chance forecast keyed by (circuit, rain_state, wetness)."""
        key = (circuit.name, rain_state, int(round(wetness)))
        cached = self._forecast_cache.get(key)
        if cached is not None:
            return cached
        forecast = weather_forecast(circuit, rain_state, wetness)
        self._forecast_cache[key] = forecast
        return forecast

    def _grid_rows(self) -> List[dict]:
        if not self._grid:
            return []
        # Rebuild the tyre-selection grid from the ordered driver names so it
        # doesn't depend on a live qualifying object (needed after loading a
        # save that skipped/stored the grid).
        teams_by_driver = {d.name: d.team.name for d in self.drivers}
        return [
            {
                "position": idx,
                "driver": name,
                "team": teams_by_driver.get(name, ""),
                "best_lap": None,
                "eliminated": False,
            }
            for idx, name in enumerate(self._grid, 1)
        ]

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
                finished=True,
                phase=self.phase or "selection",
                season_finished=self.season.season_finished,
                player_team_id=self._player_team_id(),
                classification=[],
                events=[],
                **self._season_context(),
            )

        # If race has finished, prefer the final classification from the engine
        finished = is_race_finished(self.race)

        if finished:
            # ensure points and season summary are finalized before exposing state
            if not self._race_finalized:
                self._finalize_race()
                self._race_finalized = True

            table_source = final_classification(self.race)
            snapshot = {
                "lap": self.race.get("lap", 0),
                "laps": self.race["circuit"].laps,
                "weather": self.race.get("weather", ""),
                "table": table_source,
                "events": self._race_events,
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
            "events": self._race_events,
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
        self.analytics_svc.record(snapshot)

        # accumulate events across the race (capped)
        lap = snapshot.get("lap", 0)
        for message in snapshot.get("events", []):
            self._race_events.append((lap, message))
        if len(self._race_events) > MAX_EVENTS:
            self._race_events = self._race_events[-MAX_EVENTS:]

        # If the race finishes as a result of this lap, ensure final classification is used
        if is_race_finished(self.race):
            # final_classification returns ordered list of states
            final_table = final_classification(self.race)
            snapshot = {
                "lap": self.race.get("lap", 0),
                "laps": self.race["circuit"].laps,
                "weather": self.race.get("weather", ""),
                "table": final_table,
                "events": self._race_events,
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
        classification = final_classification(self.race)
        self.season.award_points(classification)

        race_summary = {
            "circuit": self.race["circuit"].name,
            "lap": self.race.get("lap", 0),
            "classification": [build_driver_state(s) for s in classification],
            "events": [message for _, message in self._race_events],
        }
        self.season.add_result(race_summary)
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
        if self.season.advance_circuit():
            # season finished
            self.phase = "season_finished"
            return self.get_state()

        # start the next weekend (qualifying first)
        self._start_weekend()
        return self.get_state()

    def get_standings(self) -> List[dict]:
        return self.season.get_standings()

    def get_constructor_standings(self) -> List[dict]:
        return self.season.get_constructor_standings()

    def get_season_results(self) -> List[dict]:
        return self.season.season_results

    def is_season_finished(self) -> bool:
        return self.season.season_finished
    def get_calendar(self) -> dict:
        """Return the season calendar: circuits, current index, season state,
        and a lean per-race podium (top-3 finishers with points)."""
        pts = self.season.PTS
        results = []
        for summary in self.season.season_results:
            podium = []
            run_idx = 0
            for s in summary["classification"]:
                if s.status != "Running":
                    continue
                points = pts[run_idx] if run_idx < len(pts) else 0
                if run_idx < 3:
                    podium.append(
                        {
                            "position": s.position,
                            "driver": s.driver,
                            "team": s.team,
                            "points": points,
                        }
                    )
                run_idx += 1
            results.append({"circuit": summary["circuit"], "podium": podium})
        return {
            "circuits": [
                {
                    "name": c.name,
                    "laps": c.laps,
                    "base_lap_time": c.base_lap_time,
                    "engine_factor": c.engine_factor,
                    "aero_factor": c.aero_factor,
                    "rain_chance_multiplier": c.rain_chance_multiplier,
                }
                for c in self.season.circuits
            ],
            "current_index": self.season.circuit_index,
            "season_finished": self.season.season_finished,
            "results": results,
        }

    def analytics(self) -> dict:
        return self.analytics_svc.data()

    def export_csv(self) -> str:
        return self.analytics_svc.export_csv()

    def _build_state(self, snapshot: dict) -> RaceState:
        classification = build_classification(snapshot["table"])
        events = [RaceEvent(lap=lap, message=message) for lap, message in self._race_events]

        finished = is_race_finished(self.race)
        sc = self.race.get("safety_car", False) if self.race else snapshot.get("safety_car", False)
        rf = self.race.get("red_flag_stoppage", False) if self.race else snapshot.get("red_flag", False)

        return RaceState(
            race_name=self.race["circuit"].name,
            lap=snapshot.get("lap", 0),
            total_laps=snapshot.get("laps", self.race["circuit"].laps),
            weather=snapshot.get("weather", ""),
            weather_forecast=self._forecast(self.race["circuit"], self.race["rain_state"], self.race["track_wetness"]),
            safety_car=sc,
            red_flag=rf,
            finished=finished,
            phase=self.phase,
            season_finished=self.season.season_finished,
            grid=self._grid,
            starting_tyres=self._starting_tyres,
            player_team_id=self._player_team_id(),
            classification=classification,
            events=events,
            **self._season_context(),
        )

    # --- save / load -------------------------------------------------------
    def save_meta(self) -> dict:
        """Describe the saved game (for the Settings UI), or the live state if
        nothing has been saved yet."""
        data = {}
        if SAVE_PATH.exists():
            try:
                data = json.loads(SAVE_PATH.read_text())
            except (ValueError, OSError):
                data = {}
        meta = {"exists": SAVE_PATH.exists()}
        if meta["exists"]:
            st = SAVE_PATH.stat()
            meta["saved_at"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
        team_id = data.get("player_team_id", self._player_team_id())
        meta["player_team_id"] = team_id
        meta["player_team"] = None
        if team_id is not None:
            team = self.season.team_object(team_id)
            if team is not None:
                meta["player_team"] = team.name
        meta["circuit"] = self.season.current_circuit().name
        meta["circuit_index"] = self.season.circuit_index
        meta["total_circuits"] = len(self.season.circuits)
        race = data.get("race")
        meta["lap"] = None
        if isinstance(race, dict):
            meta["lap"] = race.get("lap", 0)
        elif self.race is not None:
            meta["lap"] = self.race.get("lap", 0)
        meta["phase"] = data.get("phase") if data else self.phase
        return meta

    def export_save(self) -> dict:
        """Serialize the entire playable state to a JSON-able dict.

        Used by both the server-side save file and the client-side (browser)
        save so each player can keep their own game in localStorage.
        """
        data = {
            "version": 1,
            "phase": self.phase,
            "player_team_id": self._player_team_id(),
            "season": {
                "circuit_index": self.season.circuit_index,
                "standings": dict(self.season._standings),
                "constructor_standings": dict(self.season._constructor_standings),
                "season_results": _to_jsonable(self.season._season_results),
                "season_finished": self.season.season_finished,
            },
            "weekend": {
                "wetness": self._weekend_wetness,
                "weather": self._weekend_weather,
                "starting_tyres": dict(self._starting_tyres),
                "grid": list(self._grid) if self._grid else None,
            },
        }
        if self.race is not None:
            data["race"] = _to_jsonable(self.race)
            data["race_events"] = _to_jsonable(self._race_events)
            data["race_finalized"] = self._race_finalized
            data["analytics"] = _to_jsonable(self.analytics_svc._history)
        else:
            data["race"] = None
            data["race_events"] = []
            data["race_finalized"] = False
            data["analytics"] = []
        return data

    def save_game(self) -> dict:
        """Persist the entire playable state to a JSON file."""
        data = self.export_save()
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return self.save_meta()

    def load_game(self, data: Optional[dict] = None) -> RaceState:
        """Restore a saved game into the live service and return its state.

        Pass `data` (a JSON-able dict) to restore a client-supplied save, e.g.
        one stored in a browser's localStorage. With no argument the game is
        restored from the on-disk save file.

        Qualifying is recreated from the saved weekend weather (mid-session
        qualifying progress is not persisted); everything else — the race,
        season standings/results and analytics history — is restored exactly.
        """
        if data is None:
            if not SAVE_PATH.exists():
                raise FileNotFoundError("No save file found. Start a season and save first.")
            data = json.loads(SAVE_PATH.read_text())
        if data.get("version") != 1:
            raise ValueError("Unsupported save version.")

        drivers_by_name, teams_by_id, circuits_by_name = build_lookup(self.drivers, self.circuits)

        # Season + player team
        season = data["season"]
        self.season._circuit_index = int(season["circuit_index"])
        self.season._standings = dict(season["standings"])
        self.season._constructor_standings = dict(season["constructor_standings"])
        self.season._season_results = _from_jsonable(
            season["season_results"], drivers_by_name, teams_by_id, circuits_by_name
        )
        self.season._season_finished = bool(season["season_finished"])
        team_id = data.get("player_team_id")
        self.player_team = self.season.team_object(team_id) if team_id is not None else None
        self.season.player_team = self.player_team

        # Weekend context
        self._weekend_wetness = float(data["weekend"]["wetness"])
        self._weekend_weather = data["weekend"]["weather"]
        self._starting_tyres = dict(data["weekend"].get("starting_tyres", {}))
        self._grid = list(data["weekend"].get("grid") or []) or None

        self._forecast_cache = {}
        self._last_snapshot = None
        self._race_finalized = bool(data.get("race_finalized", False))
        self._race_events = _from_jsonable(
            data.get("race_events", []), drivers_by_name, teams_by_id, circuits_by_name
        ) or []
        self.analytics_svc._history = _from_jsonable(
            data.get("analytics", []), drivers_by_name, teams_by_id, circuits_by_name
        ) or []

        self.phase = data["phase"]
        if self.phase == "qualifying":
            self.race = None
            self._qualifying = create_qualifying(
                self.drivers, self.season.current_circuit(), track_wetness=self._weekend_wetness
            )
        elif self.phase == "tyre_selection":
            self.race = None
            self._qualifying = minimal_qualifying(self._weekend_wetness, self._weekend_weather)
        elif self.phase in ("race", "season_finished"):
            race = _from_jsonable(data.get("race"), drivers_by_name, teams_by_id, circuits_by_name)
            if not race:
                raise ValueError("Save has no race state.")
            # The RNG can't be serialized; start fresh randomness on load.
            race["rng"] = random.Random()
            self.race = race
            self._qualifying = minimal_qualifying(self._weekend_wetness, self._weekend_weather)
        else:
            self.race = None
            self._qualifying = None

        return self.get_state()


# Singleton used by the FastAPI router
race_service = RaceService()
