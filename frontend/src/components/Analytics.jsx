import { useEffect, useState, useMemo, useRef } from "react";
import { api } from "../api";
import { getSeriesColor } from "../utils/teamData";
import { tyreOrder, TYRE_LABELS } from "../utils/tyres";

const METRICS = [
  { key: "pace", label: "Pace by Lap", unit: "Time" },
  { key: "position", label: "Position by Lap", unit: "Pos" },
  { key: "gap", label: "Gap to Leader", unit: "Seconds" },
  { key: "tyre", label: "Tyre Compound by Lap", unit: "Compound" },
];

function formatLapTime(seconds) {
  if (seconds == null || isNaN(seconds) || seconds === 0) return "-";
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(3);
  return `${mins}:${secs.padStart(6, "0")}`;
}

function formatGap(val) {
  if (val == null) return "-";
  if (val === 0) return "Leader";
  return `+${val.toFixed(3)}s`;
}

// Measure the actual rendered size of a container so the chart can fill it 1:1.
function useContainerSize(initialWidth, initialHeight) {
  const ref = useRef(null);
  const [size, setSize] = useState({ width: initialWidth, height: initialHeight });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const update = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (w > 0 && h > 0) {
        setSize((prev) => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
      }
    };

    update();
    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(update);
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return [ref, size];
}

// Interactive Chart Component (hoisted so it never remounts on parent re-renders)
export function InteractiveChart({ series, scLaps, metric, zoomDomain, setZoomDomain }) {
  const [plotRef, { width, height }] = useContainerSize(1400, 560);
  const padLeft = 78;
  const padRight = 30;
  const padTop = 40;
  const padBottom = 55;

  const [hoverLap, setHoverLap] = useState(null);
  const [tooltipPos, setTooltipPos] = useState(null);
  const [dragState, setDragState] = useState(null); // { startX, startY, currentX, currentY }

  // Get tooltip driver rows for hoverLap
  const tooltipData = useMemo(() => {
    if (hoverLap == null) return null;
    const isSC = scLaps.includes(hoverLap);
    const rows = [];
    series.forEach((s) => {
      const pt = s.points.find((p) => p.x === hoverLap);
      if (pt && pt.y != null) {
        let valFormatted = "";
        if (metric === "pace") valFormatted = formatLapTime(pt.y);
        else if (metric === "position") valFormatted = `P${pt.y}`;
        else if (metric === "gap") valFormatted = formatGap(pt.y);
        else if (metric === "tyre") {
          const compoundName = TYRE_LABELS[pt.y] || "Unknown";
          const age = pt.raw?.tyre_age != null ? ` (d${pt.raw.tyre_age})` : "";
          valFormatted = `${compoundName}${age}`;
        }

        rows.push({
          name: s.name,
          team: s.team,
          color: getSeriesColor(s),
          val: pt.y,
          valFormatted,
          raw: pt.raw,
        });
      }
    });

    // Sort rows based on metric
    if (metric === "position") rows.sort((a, b) => a.val - b.val);
    else if (metric === "pace" || metric === "gap") rows.sort((a, b) => a.val - b.val);

    return { lap: hoverLap, isSC, rows };
  }, [hoverLap, series, metric, scLaps]);

  if (!series || series.length === 0) {
    return <div className="chart-empty">Select drivers to view interactive telemetry</div>;
  }

  const allPoints = series.flatMap((s) => s.points);
  const xs = allPoints.map((p) => p.x).filter((v) => v != null);
  const ys = allPoints.map((p) => p.y).filter((v) => v != null);

  if (xs.length === 0) {
    return <div className="chart-empty">No telemetry data available for selected drivers.</div>;
  }

  const fullXMin = Math.min(...xs);
  const fullXMax = Math.max(...xs);

  let fullYMin, fullYMax;
  if (metric === "tyre") {
    fullYMin = 1;
    fullYMax = 5;
  } else if (metric === "position") {
    fullYMin = 1;
    fullYMax = Math.max(10, ...ys);
  } else if (metric === "pace") {
    fullYMin = Math.min(...ys) * 0.98;
    fullYMax = Math.max(...ys) * 1.02;
  } else {
    fullYMin = 0;
    fullYMax = Math.max(...ys) * 1.05;
  }

  const xMin = zoomDomain?.xMin ?? fullXMin;
  const xMax = zoomDomain?.xMax ?? fullXMax;
  const yMin = zoomDomain?.yMin ?? fullYMin;
  const yMax = zoomDomain?.yMax ?? fullYMax;

  const xScale = (v) => padLeft + ((v - xMin) / (xMax - xMin || 1)) * (width - padLeft - padRight);
  const yScale = (v) => {
    if (metric === "position") {
      return padTop + ((v - yMin) / (yMax - yMin || 1)) * (height - padTop - padBottom);
    }
    return padTop + ((yMax - v) / (yMax - yMin || 1)) * (height - padTop - padBottom);
  };

  const xInverse = (px) => {
    const clampedPx = Math.max(padLeft, Math.min(width - padRight, px));
    return xMin + ((clampedPx - padLeft) / (width - padLeft - padRight)) * (xMax - xMin);
  };

  // Zoom Handlers
  function handleResetZoom() {
    setZoomDomain(null);
  }

  function handleWheel(e) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 0.85 : 1.18;
    const cursorXVal = xInverse(getSvgCoordinates(e).x);
    const newSpan = (xMax - xMin) * zoomFactor;
    const leftRatio = (cursorXVal - xMin) / (xMax - xMin || 1);

    let newXMin = Math.round(cursorXVal - newSpan * leftRatio);
    let newXMax = Math.round(cursorXVal + newSpan * (1 - leftRatio));

    if (newXMax - newXMin < 2) return;
    newXMin = Math.max(fullXMin, newXMin);
    newXMax = Math.min(fullXMax, newXMax);

    if (newXMin <= fullXMin && newXMax >= fullXMax) {
      setZoomDomain(null);
    } else {
      setZoomDomain({ xMin: newXMin, xMax: newXMax, yMin: fullYMin, yMax: fullYMax });
    }
  }

  function getSvgCoordinates(e) {
    if (!plotRef.current) return { x: 0, y: 0 };
    const rect = plotRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
      rawX: clientX - rect.left,
      rawY: clientY - rect.top,
    };
  }

  function handleMouseDown(e) {
    if (e.button !== 0) return;
    const coords = getSvgCoordinates(e);
    if (coords.x >= padLeft && coords.x <= width - padRight) {
      setDragState({ startX: coords.x, currentX: coords.x });
    }
  }

  function handleMouseMove(e) {
    const coords = getSvgCoordinates(e);

    // Update drag box
    if (dragState) {
      setDragState((prev) => (prev ? { ...prev, currentX: coords.x } : null));
    }

    // Update hover crosshair & tooltip
    if (coords.x >= padLeft && coords.x <= width - padRight) {
      const valX = xInverse(coords.x);
      // Find nearest lap number from xs
      const availableLaps = Array.from(new Set(xs)).filter((l) => l >= xMin && l <= xMax);
      if (availableLaps.length > 0) {
        const nearestLap = availableLaps.reduce((prev, curr) => (Math.abs(curr - valX) < Math.abs(prev - valX) ? curr : prev));
        setHoverLap(nearestLap);
        setTooltipPos({ x: coords.rawX, y: coords.rawY });
      }
    } else {
      setHoverLap(null);
      setTooltipPos(null);
    }
  }

  function handleMouseUp() {
    if (dragState) {
      const minXPx = Math.min(dragState.startX, dragState.currentX);
      const maxXPx = Math.max(dragState.startX, dragState.currentX);
      if (maxXPx - minXPx > 15) {
        const lap1 = Math.round(xInverse(minXPx));
        const lap2 = Math.round(xInverse(maxXPx));
        const newMin = Math.max(fullXMin, Math.min(lap1, lap2));
        const newMax = Math.min(fullXMax, Math.max(lap1, lap2));
        if (newMax - newMin >= 1) {
          setZoomDomain({ xMin: newMin, xMax: newMax, yMin: fullYMin, yMax: fullYMax });
        }
      }
      setDragState(null);
    }
  }

  function handleMouseLeave() {
    setHoverLap(null);
    setTooltipPos(null);
    setDragState(null);
  }

  // Unique visible laps for X axis ticks
  const visibleLaps = Array.from(new Set(xs)).filter((x) => x >= xMin && x <= xMax).sort((a, b) => a - b);
  const tickStep = Math.max(1, Math.ceil(visibleLaps.length / 14));
  const xTicks = visibleLaps.filter((_, i) => i % tickStep === 0 || i === visibleLaps.length - 1);

  const isZoomed = zoomDomain != null;

  return (
    <div className="plotly-chart-wrapper">
      {/* Modebar / Controls */}
      <div className="plotly-modebar">
        <div className="modebar-info">
          {isZoomed && (
            <span className="zoomed-badge">Zoomed: Laps {xMin} – {xMax}</span>
          )}
        </div>
        <div className="modebar-buttons">
          {isZoomed && (
            <button title="Reset Zoom" onClick={handleResetZoom} className="modebar-btn reset-btn">
              🏠 Reset View
            </button>
          )}
        </div>
      </div>

      {/* SVG Container */}
      <div ref={plotRef} className="chart-canvas">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          style={{ width: "100%", height: "100%", display: "block", cursor: dragState ? "crosshair" : "default" }}
        >
          <defs>
            <linearGradient id="scGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#eab308" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#eab308" stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* Background */}
          <rect width={width} height={height} fill="#0f1419" rx={8} />

          {/* Safety Car Highlight Bands */}
          {scLaps.map((lap) => {
            if (lap < xMin || lap > xMax) return null;
            const xPos = xScale(lap);
            const bandWidth = Math.max(4, (width - padLeft - padRight) / (xMax - xMin || 1));
            return (
              <g key={`sc-${lap}`}>
                <rect
                  x={xPos - bandWidth / 2}
                  y={padTop}
                  width={bandWidth}
                  height={height - padTop - padBottom}
                  fill="url(#scGradient)"
                />
                <line
                  x1={xPos}
                  y1={padTop}
                  x2={xPos}
                  y2={height - padBottom}
                  stroke="#eab308"
                  strokeWidth={1}
                  strokeDasharray="2,2"
                  opacity={0.6}
                />
              </g>
            );
          })}

          {/* Grid & Axis Lines */}
          <line x1={padLeft} y1={height - padBottom} x2={width - padRight} y2={height - padBottom} stroke="#374151" strokeWidth={2} />
          <line x1={padLeft} y1={padTop} x2={padLeft} y2={height - padBottom} stroke="#374151" strokeWidth={2} />

          {/* X-Axis Ticks & Labels */}
          {xTicks.map((x) => (
            <g key={x} transform={`translate(${xScale(x)},${height - padBottom})`}>
              <line y2={6} stroke="#374151" />
              <text y={20} x={0} textAnchor="middle" fontSize={13} fill="#9ca3af" fontWeight="600">{x}</text>
            </g>
          ))}

          {/* Y-Axis Labels */}
          {metric === "tyre" && [1, 2, 3, 4, 5].map((v) => (
            <g key={v} transform={`translate(${padLeft - 10},${yScale(v)})`}>
              <text x={0} y={4} textAnchor="end" fontSize={13} fill="#9ca3af" fontWeight="600">{TYRE_LABELS[v]}</text>
            </g>
          ))}

          {metric !== "tyre" && (() => {
            const ticks = 5;
            const step = (yMax - yMin) / (ticks - 1 || 1);
            return Array.from({ length: ticks }).map((_, i) => {
              const v = metric === "position" ? Math.round(yMin + i * step) : yMin + i * step;
              const yPos = yScale(v);
              let labelText = "";
              if (metric === "pace") labelText = formatLapTime(v);
              else if (metric === "position") labelText = `P${v}`;
              else if (metric === "gap") labelText = formatGap(v);

              return (
                <g key={i}>
                  <line x1={padLeft} y1={yPos} x2={width - padRight} y2={yPos} stroke="#273244" strokeDasharray="4,4" />
                    <text x={padLeft - 10} y={yPos + 4} textAnchor="end" fontSize={13} fill="#9ca3af">
                    {labelText}
                  </text>
                </g>
              );
            });
          })()}

          {/* Data Paths */}
          {series.map((s) => {
            const color = getSeriesColor(s);
            const validPoints = s.points.filter((p) => p.y != null && p.x >= xMin && p.x <= xMax);
            const pathD = validPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x)} ${yScale(p.y)}`).join(" ");

            return (
              <g key={s.name}>
                <path d={pathD} stroke={color} fill="none" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
                {validPoints.map((p, i) => (
                  <circle
                    key={i}
                    cx={xScale(p.x)}
                    cy={yScale(p.y)}
                    r={hoverLap === p.x ? 6 : 3.5}
                    fill={hoverLap === p.x ? "#fff" : color}
                    stroke={color}
                    strokeWidth={2}
                  />
                ))}
              </g>
            );
          })}

          {/* Crosshair Guideline */}
          {hoverLap != null && hoverLap >= xMin && hoverLap <= xMax && (
            <g>
              <line
                x1={xScale(hoverLap)}
                y1={padTop}
                x2={xScale(hoverLap)}
                y2={height - padBottom}
                stroke="#9ca3af"
                strokeWidth={1.5}
                strokeDasharray="4,4"
              />
            </g>
          )}

          {/* Drag Selection Box */}
          {dragState && (
            <rect
              x={Math.min(dragState.startX, dragState.currentX)}
              y={padTop}
              width={Math.abs(dragState.currentX - dragState.startX)}
              height={height - padTop - padBottom}
              fill="rgba(225, 6, 0, 0.2)"
              stroke="#e10600"
              strokeWidth={1}
            />
          )}
        </svg>

        {/* Plotly-Style Floating Tooltip */}
        {tooltipData && tooltipPos && (
          <div
            className="plotly-tooltip"
            style={{
              top: Math.min(tooltipPos.y + 15, height - 180),
              left: tooltipPos.x > width / 2 ? tooltipPos.x - 240 : tooltipPos.x + 15,
            }}
          >
            <div className="tooltip-header">
              <span>Lap {tooltipData.lap}</span>
              {tooltipData.isSC && <span className="tooltip-sc-tag">⚠️ SAFETY CAR</span>}
            </div>
            <div className="tooltip-body">
              {tooltipData.rows.map((r) => (
                <div key={r.name} className="tooltip-row">
                  <div className="tooltip-driver">
                    <span className="driver-color-dot" style={{ background: r.color }}></span>
                    <span className="driver-name">{r.name}</span>
                  </div>
                  <span className="tooltip-val">{r.valFormatted}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Analytics({ race, playerTeam }) {
  const [telemetry, setTelemetry] = useState(null);
  const [selectedDrivers, setSelectedDrivers] = useState([]);
  const [metric, setMetric] = useState("pace");
  const [zoomDomain, setZoomDomain] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const analyticsRef = useRef(null);

  // Fill the viewport below the header so the chart uses the whole screen.
  useEffect(() => {
    const el = analyticsRef.current;
    if (!el) return;
    const update = () => {
      const top = el.getBoundingClientRect().top;
      el.style.height = `${Math.max(640, window.innerHeight - top - 4)}px`;
    };
    update();
    window.addEventListener("resize", update);
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(update) : null;
    if (ro) ro.observe(el);
    return () => {
      window.removeEventListener("resize", update);
      if (ro) ro.disconnect();
    };
  }, [race, telemetry]);

  // Load telemetry from backend
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

  // Close dropdown on outside click
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

  // Build series data for chart
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

  if (!telemetry) return <div style={{ padding: 20, textAlign: "center", color: "#9ca3af" }}>Loading analytics telemetry...</div>;

  const triggerLabel = selectedDrivers.length === 0
    ? "Select drivers…"
    : selectedDrivers.length === driversList.length
    ? `All drivers (${driversList.length})`
    : null;

  return (
    <div className="analytics" ref={analyticsRef}>
      <div className="analytics-head">
        <h2>Race Telemetry &amp; Analytics</h2>
        <span className="analytics-driver-count">
          {selectedDrivers.length} / {driversList.length} drivers shown
        </span>
      </div>

      {/* Controls bar */}
      <div className="analytics-controls-bar">

        {/* Driver multi-select dropdown */}
        <div className="driver-dropdown-wrap" ref={dropdownRef}>
          <label className="ctrl-label" htmlFor="driver-multiselect">Drivers</label>
          <div
            id="driver-multiselect"
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

        {/* Metric selector */}
        <div className="metric-select-wrap">
          <label className="ctrl-label">Metric</label>
          <select
            className="metric-select"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            {METRICS.map((m) => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Full-width chart filling remaining screen height */}
      <div className="analytics-chart">
        <InteractiveChart series={series} scLaps={scLaps} metric={metric} zoomDomain={zoomDomain} setZoomDomain={setZoomDomain} />
      </div>
    </div>
  );
}
