import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { InteractiveChart } from "./Analytics";
import { getSeriesColor } from "../utils/teamData";
import { tyreOrder } from "../utils/tyres";

const METRICS = [
  { key: "pace", label: "Pace" },
  { key: "position", label: "Position" },
  { key: "gap", label: "Gap" },
  { key: "tyre", label: "Tyre" },
];

export default function TelemetryChart({ race, playerTeam }) {
  const [telemetry, setTelemetry] = useState(null);
  const [selectedDrivers, setSelectedDrivers] = useState([]);
  const [metric, setMetric] = useState("pace");
  const [zoomDomain, setZoomDomain] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

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

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const driversList = useMemo(() => Object.keys((telemetry && telemetry.per_driver) || {}), [telemetry]);

  const driversInitRef = useRef(false);
  const driversKeyRef = useRef("");

  useEffect(() => {
    if (!driversList || driversList.length === 0) return;
    const key = driversList.join(",");
    if (!driversInitRef.current) {
      driversInitRef.current = true;
      driversKeyRef.current = key;
      if (playerTeam && playerTeam.drivers && playerTeam.drivers.length) {
        const names = playerTeam.drivers.map((d) => d.name).filter((n) => driversList.includes(n));
        if (names.length) {
          setSelectedDrivers(names);
          return;
        }
      }
      setSelectedDrivers(driversList.slice(0, 3));
      return;
    }
    if (driversKeyRef.current !== key) {
      driversKeyRef.current = key;
      setSelectedDrivers((s) => s.filter((n) => driversList.includes(n)));
    }
  }, [driversList, playerTeam]);

  function toggleDriver(name) {
    setSelectedDrivers((s) => (s.includes(name) ? s.filter((x) => x !== name) : [...s, name]));
  }

  function selectAll() {
    setSelectedDrivers(driversList);
  }

  function selectNone() {
    setSelectedDrivers([]);
  }

  function selectMyTeam() {
    if (playerTeam && playerTeam.drivers) {
      const names = playerTeam.drivers.map((d) => d.name).filter((n) => driversList.includes(n));
      setSelectedDrivers(names);
    }
  }

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
        points = laps.map((l) => ({ x: l.lap, y: tyreOrder(l.tyre), raw: l }));
      }

      return { name: d, points, team };
    });
  }, [telemetry, selectedDrivers, metric]);

  const scLaps = useMemo(() => (telemetry && telemetry.sc_laps) || [], [telemetry]);

  const triggerLabel = selectedDrivers.length === 0
    ? "Select drivers…"
    : selectedDrivers.length === driversList.length
    ? `All drivers (${driversList.length})`
    : null;

  return (
    <div className="sidebar-telemetry">
      <div className="telemetry-controls">
        <div className="driver-dropdown-wrap telemetry-driver-pick" ref={dropdownRef}>
          <div
            role="combobox"
            aria-expanded={dropdownOpen}
            aria-haspopup="listbox"
            aria-label="Select drivers to display"
            className={`driver-dropdown-trigger ${dropdownOpen ? "open" : ""}`}
            onClick={() => setDropdownOpen((o) => !o)}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setDropdownOpen((o) => !o);
              }
            }}
          >
            <div className="driver-tags">
              {triggerLabel ? (
                <span className="driver-tag-placeholder">{triggerLabel}</span>
              ) : (
                selectedDrivers.map((d) => {
                  const s = series.find((s) => s.name === d);
                  const color = s ? getSeriesColor(s) : "#9ca3af";
                  return (
                    <span key={d} className="driver-tag" style={{ borderColor: color, background: `${color}22` }}>
                      <span className="driver-tag-dot" style={{ background: color }} />
                      {d}
                      <button
                        className="driver-tag-remove"
                        onClick={(e) => { e.stopPropagation(); toggleDriver(d); }}
                      >×</button>
                    </span>
                  );
                })
              )}
            </div>
            <span className="dropdown-arrow">{dropdownOpen ? "▲" : "▼"}</span>
          </div>

          {dropdownOpen && (
            <div className="driver-dropdown-panel" role="listbox" aria-label="Drivers">
              <div className="dropdown-actions">
                <button onClick={selectAll}>All</button>
                <button onClick={selectMyTeam}>My Team</button>
                <button onClick={selectNone}>Clear</button>
              </div>
              <div className="dropdown-list">
                {driversList.map((d) => {
                  const s = series.find((s) => s.name === d);
                  const color = s ? getSeriesColor(s) : "#9ca3af";
                  const active = selectedDrivers.includes(d);
                  return (
                    <div
                      key={d}
                      role="option"
                      aria-selected={active}
                      className={`dropdown-item ${active ? "active" : ""}`}
                      onClick={() => toggleDriver(d)}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggleDriver(d);
                        }
                      }}
                    >
                      <span className="dropdown-item-dot" style={{ background: active ? color : "#374151", borderColor: color }} />
                      <span className="dropdown-item-name">{d}</span>
                      {active && <span className="dropdown-item-check">✓</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <select
          className="metric-select sidebar-metric telemetry-metric"
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
