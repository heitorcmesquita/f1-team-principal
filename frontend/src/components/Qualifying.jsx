import { useEffect, useRef, useState } from "react";
import LogoImg from "./LogoImg";
import { formatWeather } from "../utils/weather";

const SPEED_OPTIONS = [5, 10, 20, 30];
const PHASES = ["Q1", "Q2", "Q3"];

function fmtCountdown(secs) {
  const s = Math.max(0, Math.floor(secs || 0));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function fmtLap(t) {
  if (t == null) return "No time";
  const m = Math.floor(t / 60);
  const s = (t - m * 60).toFixed(3);
  return `${m}:${String(s).padStart(6, "0")}`;
}

function formatEvent(msg) {
  return String(msg).replace(/\bmacio\b/gi, "Soft").replace(/\bmedio\b/gi, "Medium");
}

export default function Qualifying({ race, playerTeam, onTick, onSkip }) {
  const q = race.qualifying || {};
  const rows = q.classification || [];
  const onTrackCount = rows.filter((r) => r.on_track).length;
  const busyRef = useRef(false);
  const prevPhaseRef = useRef(q.phase);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(10);

  useEffect(() => {
    const prev = prevPhaseRef.current;
    const cur = q.phase;
    if (prev && cur && cur !== prev && !q.finished) {
      setPaused(true);
    }
    prevPhaseRef.current = cur;
  }, [q.phase, q.finished]);

  useEffect(() => {
    if (paused || q.finished) return undefined;
    busyRef.current = false;
    const id = setInterval(() => {
      if (busyRef.current) return;
      busyRef.current = true;
      Promise.resolve(onTick(speed)).finally(() => {
        busyRef.current = false;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [paused, onTick, q.finished, speed]);

  const playerName = playerTeam?.name;
  const currentPhaseIndex = PHASES.indexOf(q.phase);

  return (
    <div className="qualifying-screen">
      <div className="quali-head">
        <div className="quali-phase">
          <span className="quali-phase-label">Qualifying</span>
          <h2>{q.finished ? "Grid Set" : q.phase || "Q1"}</h2>
          <div className="quali-timer">
            {q.finished ? "Done" : paused ? "Paused" : fmtCountdown(q.time_left)}
          </div>
        </div>

        <div className="quali-stats">
          <div className="quali-stat">
            <span className="quali-stat-label">Weather</span>
            <strong>{formatWeather(q.weather)}</strong>
          </div>
          <div className="quali-stat">
            <span className="quali-stat-label">On Track</span>
            <strong>{onTrackCount} / {rows.length}</strong>
          </div>
        </div>

        <div className="quali-actions">
          <label className="speed-label">
            Speed
            <select
              className="speed-select"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              disabled={q.finished}
            >
              {SPEED_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}x</option>
              ))}
            </select>
          </label>

          {paused && !q.finished && (
            <button className="continue-btn" onClick={() => setPaused(false)}>
              Continue to {q.phase}
            </button>
          )}
          <button
            className="skip-btn"
            onClick={() => onSkip("Q2")}
            disabled={q.finished || currentPhaseIndex >= 1}
          >
            Skip Q2
          </button>
          <button
            className="skip-btn"
            onClick={() => onSkip("Q3")}
            disabled={q.finished || currentPhaseIndex >= 2}
          >
            Skip Q3
          </button>
          <button className="skip-btn" onClick={() => onSkip("end")} disabled={q.finished}>
            Skip End
          </button>
        </div>
      </div>

      <div className="quali-body">
        <div className="quali-table-wrap">
          <table className="quali-table">
            <thead>
              <tr>
                <th>Pos</th>
                <th>Driver</th>
                <th>Team</th>
                <th>Best Lap</th>
                <th>Runs</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.driver}
                  className={
                    r.eliminated
                      ? "quali-eliminated"
                      : r.on_track
                      ? "quali-ontrack"
                      : playerName && r.team === playerName
                      ? "quali-player"
                      : ""
                  }
                >
                  <td className="quali-pos">{r.position}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <LogoImg teamName={r.team} size="20px" alt={r.team} />
                      <strong>{r.driver}</strong>
                    </div>
                  </td>
                  <td className="quali-team">{r.team}</td>
                  <td className="quali-time">{fmtLap(r.best_lap)}</td>
                  <td>{r.runs_done}</td>
                  <td>
                    {r.on_track ? (
                      <span className="quali-status-ontrack">ON TRACK</span>
                    ) : r.eliminated ? (
                      <span className="quali-status-out">OUT</span>
                    ) : (
                      <span className="quali-status-garage">GARAGE</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="quali-side">
          {(q.eliminated || []).length > 0 && (
            <div className="quali-panel">
              <h3>Eliminated</h3>
              <ul className="quali-eliminated-list">
                {q.eliminated.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="quali-panel">
            <h3>Session Events</h3>
            <div className="quali-events">
              {(q.events || []).length === 0 ? (
                <p className="empty-events">Waiting for drivers to leave the garage...</p>
              ) : (
                [...(q.events || [])]
                  .slice(-14)
                  .reverse()
                  .map((ev, i) => (
                    <div key={i} className="quali-event-item">
                      {formatEvent(ev)}
                    </div>
                  ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
