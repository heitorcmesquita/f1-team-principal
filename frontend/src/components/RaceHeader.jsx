import LogoImg from "./LogoImg";
import { getCircuitFlagPath } from "../utils/circuitFlags";
import { formatWeather } from "../utils/weather";

const COMPOUNDS = [
  { name: "Soft", color: "#e10600" },
  { name: "Medium", color: "#E9C46A" },
  { name: "Hard", color: "#E5E7EB" },
  { name: "Intermediate", color: "#00C2A8" },
  { name: "Wet", color: "#2B7CE0" },
];

const PACE = [
  { compound: "Soft", color: "#e10600", delta: 0 },
  { compound: "Medium", color: "#E9C46A", delta: 0.45 },
  { compound: "Hard", color: "#E5E7EB", delta: 0.85 },
];

const RAIN_HORIZONS = [5, 10, 20];

function fmtPace(delta) {
  if (delta === 0) return "base";
  return `${delta > 0 ? "+" : ""}${delta.toFixed(2)}`;
}

export default function RaceHeader({ race, playerTeam }) {
  const circuitFlag = getCircuitFlagPath(race.race_name);
  const forecast = race.weather_forecast || {};

  let session;
  if (race.phase === "qualifying") {
    session = race.qualifying?.phase || "Q1";
  } else if (race.phase === "tyre_selection") {
    session = "GRID";
  } else if (race.phase === "selection") {
    session = "TEAMS";
  } else {
    session = `LAP ${race.lap}/${race.total_laps}`;
  }

  return (
    <header className="race-header">
      <div className="race-header-title">
        {circuitFlag && (
          <img src={circuitFlag} alt={`${race.race_name} flag`} className="race-flag" />
        )}
        <h1>{race.race_name}</h1>
      </div>

      {playerTeam && (
        <div className="race-header-team">
          <LogoImg teamName={playerTeam.name} size="20px" alt={playerTeam.name} />
          <span className="race-header-team-name">{playerTeam.name}</span>
        </div>
      )}

      <div className="race-header-stat">
        <span className="race-header-stat-label">Weather</span>
        <span className="race-header-stat-value">{formatWeather(race.weather)}</span>
      </div>

      <div className="race-header-compounds">
        {COMPOUNDS.map((c) => (
          <span className="compound-chip" key={c.name}>
            <span className="compound-dot" style={{ backgroundColor: c.color }} />
            {c.name}
          </span>
        ))}
      </div>

      <div className="race-header-pace">
        <span className="race-header-stat-label">Pace</span>
        {PACE.map((p) => (
          <span className="pace-inline" style={{ color: p.color }} key={p.compound}>
            {p.compound[0]} {fmtPace(p.delta)}
          </span>
        ))}
      </div>

      <div className="race-header-rain">
        <span className="race-header-stat-label">Rain</span>
        {RAIN_HORIZONS.map((h) => (
          <span className="rain-inline" key={h}>
            {h}L{" "}
            <b>{forecast[String(h)] != null ? `${forecast[String(h)]}%` : "-"}</b>
          </span>
        ))}
      </div>

      <div className="race-header-status">
        {race.safety_car && (
          <span className="sc-badge">
            <span className="sc-pulse"></span>
            SC
          </span>
        )}
        {race.red_flag && (
          <span className="rf-badge">
            <span className="rf-pulse"></span>
            RF
          </span>
        )}
        <span className="race-header-stat-label">Session</span>
        <span className="race-header-session">{session}</span>
      </div>
    </header>
  );
}
