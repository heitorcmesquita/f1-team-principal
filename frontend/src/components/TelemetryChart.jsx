import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { InteractiveChart } from "./Analytics";

const METRICS = [
  { key: "pace", label: "Pace" },
  { key: "position", label: "Position" },
  { key: "gap", label: "Gap" },
  { key: "tyre", label: "Tyre" },
];

const TYRE_ORDER = {
  soft: 1, macio: 1,
  medium: 2, medio: 2, médio: 2,
  hard: 3, duro: 3,
  intermediate: 4, intermediario: 4, intermediário: 4,
  wet: 5, chuva: 5,
};

export default function TelemetryChart({ race, playerTeam }) {
  const [telemetry, setTelemetry] = useState(null);
  const [selectedDrivers, setSelectedDrivers] = useState([]);
  const [metric, setMetric] = useState("pace");
  const [zoomDomain, setZoomDomain] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const resp = await api.get("/race/analytics");
        if (!mounted) return;
        setTelemetry(resp.data);
      } catch (err) {
        console.error(err);
      }
    }
    load();
    return () => (mounted = false);
  }, [race]);

  const driversList = useMemo(() => Object.keys((telemetry && telemetry.per_driver) || {}), [telemetry]);

  useEffect(() => {
    if (!driversList || driversList.length === 0) return;
    if (playerTeam && playerTeam.drivers && playerTeam.drivers.length) {
      const names = playerTeam.drivers.map((d) => d.name).filter((n) => driversList.includes(n));
      if (names.length) {
        setSelectedDrivers(names);
        return;
      }
    }
    setSelectedDrivers(driversList.slice(0, 3));
  }, [driversList, playerTeam]);

  const series = useMemo(() => {
    if (!telemetry) return [];
    return selectedDrivers.map((d) => {
      const laps = telemetry.per_driver[d] || [];
      let team = "Unknown";
      if (laps.length > 0 && laps[0].team) {
        team = laps[0].team;
      }

      let points = [];
      if (metric === "pace") {
        points = laps.map((l) => ({ x: l.lap, y: l.lap_time == null ? null : l.lap_time, raw: l }));
      } else if (metric === "position") {
        points = laps.map((l) => ({ x: l.lap, y: l.position == null ? null : Number.parseInt(l.position, 10), raw: l }));
      } else if (metric === "gap") {
        points = laps.map((l) => ({ x: l.lap, y: l.gap_to_leader == null ? null : l.gap_to_leader, raw: l }));
      } else if (metric === "tyre") {
        points = laps.map((l) => ({ x: l.lap, y: TYRE_ORDER[String(l.tyre).toLowerCase()] || null, raw: l }));
      }

      return { name: d, points, team };
    });
  }, [telemetry, selectedDrivers, metric]);

  const scLaps = useMemo(() => (telemetry && telemetry.sc_laps) || [], [telemetry]);

  return (
    <div className="sidebar-telemetry">
      <div className="sidebar-telemetry-head">
        <h3>Telemetry</h3>
        <span className="sidebar-telemetry-count">
          {selectedDrivers.length} driver{selectedDrivers.length === 1 ? "" : "s"}
        </span>
        <select
          className="metric-select sidebar-metric"
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
        >
          {METRICS.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
      </div>

      <div className="sidebar-chart">
        {!telemetry ? (
          <div className="chart-empty">Loading telemetry...</div>
        ) : (
          <InteractiveChart
            series={series}
            scLaps={scLaps}
            metric={metric}
            zoomDomain={zoomDomain}
            setZoomDomain={setZoomDomain}
          />
        )}
      </div>
    </div>
  );
}
