import LogoImg from "./LogoImg";
import NavBar from "./NavBar";
import { getCircuitFlagPath } from "../utils/circuitFlags";
import { formatWeather } from "../utils/weather";
import { PACE_DELTAS } from "../utils/tyres";

const RAIN_HORIZONS = [5, 10, 20];

function fmtPace(delta) {
  if (delta === 0) return "base";
  return `${delta > 0 ? "+" : ""}${delta.toFixed(2)}`;
}

export default function RaceHeader({ race, playerTeam, onNextLap, sending, view, setView }) {
  const circuitFlag = getCircuitFlagPath(race.race_name);
  const forecast = race.weather_forecast || {};
  const round = race.circuit_index != null ? race.circuit_index + 1 : null;
  const totalRounds = race.total_circuits || null;
  const showNextLap = race.phase === "race" && !race.finished && typeof onNextLap === "function";

  let session;
  if (race.phase === "qualifying") {
    session = race.qualifying?.phase || "Q1";
  } else if (race.phase === "tyre_selection") {
    session = "GRID";
  } else if (race.phase === "selection") {
    session = "TEAMS";
  } else if (race.finished) {
    session = "FINISHED";
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

      {round != null && totalRounds != null && (
        <div className="race-header-stat race-header-round">
          <span className="race-header-stat-label">Round</span>
          <span className="race-header-stat-value">{round} / {totalRounds}</span>
        </div>
      )}

      <div className="race-header-stat">
        <span className="race-header-stat-label">Weather</span>
        <span className="race-header-stat-value">{formatWeather(race.weather)}</span>
      </div>

      <div className="race-header-pace">
        <span className="race-header-stat-label">Pace</span>
        {PACE_DELTAS.map((p) => (
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
        {showNextLap && (
          <button className="next-lap-btn header-next-lap-btn" onClick={onNextLap} disabled={sending}>
            {sending ? "Advancing..." : "Next Lap"}
          </button>
        )}
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
        <span className={`race-header-session ${race.finished ? "finished" : ""}`}>
          {session}
        </span>
      </div>

      <NavBar view={view} setView={setView} />
    </header>
  );
}
