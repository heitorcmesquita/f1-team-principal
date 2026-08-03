import { useEffect, useState } from "react";
import { api } from "../api";
import { getCircuitFlagPath } from "../utils/circuitFlags";
import { getTeamColor } from "../utils/teamData";

export default function Calendar() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let mounted = true;
    api
      .get("/race/calendar")
      .then((resp) => mounted && setData(resp.data))
      .catch(console.error);
    return () => (mounted = false);
  }, []);

  if (!data) return <div className="loading-panel">Loading calendar...</div>;

  const current = data.current_index;
  const finished = data.season_finished;
  const resultsByCircuit = {};
  (data.results || []).forEach((r) => {
    resultsByCircuit[r.circuit] = r.podium || [];
  });

  return (
    <div className="shell-panel">
      <div className="shell-panel-head">
        <h2>Race Calendar</h2>
        <span className="analytics-driver-count">
          Round {Math.min(current + 1, (data.circuits || []).length)} / {(data.circuits || []).length}
        </span>
      </div>

      <div className="calendar-list">
        {(data.circuits || []).map((c, i) => {
          const flag = getCircuitFlagPath(c.name);
          const done = i < current;
          const isNext = i === current && !finished;
          const isCurrent = i === current;
          const podium = resultsByCircuit[c.name] || [];
          return (
            <div
              key={c.name}
              className={`calendar-row ${done ? "done" : ""} ${isNext ? "next" : ""}`}
            >
              <span className="calendar-round">{i + 1}</span>
              {flag && <img src={flag} alt={`${c.name} flag`} className="calendar-flag" />}
              <span className="calendar-name">{c.name}</span>
              <span className="calendar-meta">{c.laps} laps</span>
              {podium.length > 0 && (
                <div className="calendar-podium" aria-label={`Podium: ${podium.map((p) => p.driver).join(", ")}`}>
                  {podium.map((p) => (
                    <span
                      key={p.position}
                      className="calendar-podium-entry"
                      title={`${p.driver} · ${p.points} pts`}
                    >
                      <span className="calendar-podium-pos">{p.position}</span>
                      <span
                        className="calendar-podium-name"
                        style={{ color: getTeamColor(p.team, p.driver) }}
                      >
                        {p.driver}
                      </span>
                      <span className="calendar-podium-pts">{p.points}</span>
                    </span>
                  ))}
                </div>
              )}
              <span className="calendar-badge">
                {isCurrent && !finished ? "NEXT" : done ? "DONE" : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
