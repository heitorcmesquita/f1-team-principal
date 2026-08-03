import copy
import csv
import io
from typing import Dict, List

# History is only used for analytics; capping it keeps memory bounded for a
# long season while staying far above any single race's lap count.
MAX_HISTORY = 5000


class AnalyticsService:
    """Owns the per-lap race history and derives analytics + CSV exports from it."""

    def __init__(self, drivers: list) -> None:
        self._drivers = drivers
        self._history: List[dict] = []

    def reset(self) -> None:
        self._history = []

    def record(self, snapshot: dict) -> None:
        # Store a deep copy so past snapshots don't mutate as the race advances.
        self._history.append(copy.deepcopy(snapshot))
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

    def final_snapshot(self) -> List[dict]:
        return list(self._history)

    def data(self) -> dict:
        """Return analytics data computed from lap history.

        lap history is a list of snapshots recorded after each lap.
        """
        # Build per-driver lap list
        per_driver = {d.name: [] for d in self._drivers}
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
                elif entry["tyre"] == current:
                    pass
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
