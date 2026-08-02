import { useEffect, useState } from "react";
import { api } from "../api";
import LogoImg from "./LogoImg";
import { getCircuitFlagPath } from "../utils/circuitFlags";
import { formatWeather } from "../utils/weather";

export default function ResultsScreen({ race, teams, onContinue }) {
  const [standings, setStandings] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  const driverCountry = {};
  (teams || []).forEach((t) => {
    (t.drivers || []).forEach((d) => {
      if (d.country) driverCountry[d.name] = d.country;
    });
  });

  useEffect(() => {
    async function load() {
      try {
        const s = await api.get("/race/standings");
        setStandings(s.data);
        const a = await api.get("/race/analytics");
        setAnalytics(a.data);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, [race]);

  let fastest = null;
  if (analytics && analytics.per_driver) {
    for (const [driver, laps] of Object.entries(analytics.per_driver)) {
      for (const l of laps) {
        if (l.lap_time && (!fastest || l.lap_time < fastest.lap_time)) {
          fastest = { driver, lap: l.lap, lap_time: l.lap_time };
        }
      }
    }
  }

  function fmtGap(gap) {
    if (gap === 0) return "Leader";
    if (gap == null) return "-";
    return `+${gap.toFixed(3)}`;
  }

  function fmtTime(t) {
    if (t == null) return "-";
    return t.toFixed(3);
  }

  const circuitFlag = getCircuitFlagPath(race.race_name);
  const podium = (race.classification || []).slice(0, 3);
  const podiumOrder = [podium[1], podium[0], podium[2]].filter(Boolean);

  return (
    <div className="results-screen">
      <h2 style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {circuitFlag && (
          <img
            src={circuitFlag}
            alt={`${race.race_name} flag`}
            style={{ width: "28px", height: "20px", objectFit: "cover", borderRadius: "3px" }}
          />
        )}
        <span>Race Results - {race.race_name}</span>
      </h2>

      {podiumOrder.length > 0 && (
        <div className="podium">
          {podiumOrder.map((d) => (
            <div
              key={d.driver}
              className={`podium-step ${d.position === 1 ? "podium-first" : ""}`}
            >
              <div className="podium-flag-wrap">
                {driverCountry[d.driver] ? (
                  <img
                    src={`/flags/${driverCountry[d.driver]}.svg`}
                    alt={`${d.driver} flag`}
                    className="podium-flag"
                  />
                ) : (
                  <div className="podium-flag podium-flag-empty" />
                )}
              </div>
              <div className="podium-name">{d.driver}</div>
              <div className="podium-team-row">
                <LogoImg teamName={d.team} size="18px" alt={d.team} />
                <span className="podium-team">{d.team}</span>
              </div>
              <div className={`podium-pos podium-pos-${d.position}`}>{d.position}</div>
            </div>
          ))}
        </div>
      )}

      <div className="results-grid">
        <div className="results-class">
          <h3>Final Classification</h3>
          <table>
            <thead>
              <tr>
                <th>Pos</th>
                <th>Driver</th>
                <th>Team</th>
                <th>Gap</th>
                <th>Pits</th>
              </tr>
            </thead>
            <tbody>
              {race.classification.map((d) => (
                <tr key={d.driver} style={{ backgroundColor: d.position === 1 ? "rgba(255, 213, 0, 0.08)" : "transparent" }}>
                  <td style={{ fontWeight: 700, color: d.position === 1 ? "#ffd500" : "#fff" }}>{d.position}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <LogoImg teamName={d.team} size="24px" alt={d.team} />
                      {d.driver}
                    </div>
                  </td>
                  <td>{d.team}</td>
                  <td style={{ fontWeight: d.gap === 0 ? 700 : 500, color: d.gap === 0 ? "#ffd500" : "#9ca3af" }}>{fmtGap(d.gap)}</td>
                  <td>
                    {analytics && analytics.per_driver && analytics.per_driver[d.driver] && analytics.per_driver[d.driver].length > 0
                      ? analytics.per_driver[d.driver][analytics.per_driver[d.driver].length - 1].pit_stops || 0
                      : 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="results-stats">
          <h3>Race Statistics</h3>
          <div style={{ lineHeight: 1.8 }}>
            <div>
              <strong>Fastest Lap:</strong> {fastest ? `${fastest.driver} (${fmtTime(fastest.lap_time)}s) on lap ${fastest.lap}` : "-"}
            </div>
            <div>
              <strong>Weather:</strong> {formatWeather(race.weather)}
            </div>
            <div>
              <strong>Total Laps:</strong> {race.total_laps}
            </div>
          </div>
        </div>

        <div className="results-standings">
          <h3>Drivers Championship</h3>
          {standings ? (
            <table>
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>Driver</th>
                  <th>Team</th>
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                {(standings.standings || []).map((s, index) => (
                  <tr key={s.driver}>
                    <td>{index + 1}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <LogoImg teamName={s.team} size="20px" alt={s.team} />
                        <strong>{s.driver}</strong>
                      </div>
                    </td>
                    <td>{s.team}</td>
                    <td>{s.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Loading...</p>
          )}
        </div>

        <div className="results-constructors">
          <h3>Constructors Championship</h3>
          {standings ? (
            <table>
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>Team</th>
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                {(standings.constructor_standings || []).map((s, index) => (
                  <tr key={s.team}>
                    <td>{index + 1}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <LogoImg teamName={s.team} size="20px" alt={s.team} />
                        <strong>{s.team}</strong>
                      </div>
                    </td>
                    <td>{s.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Loading...</p>
          )}
        </div>
      </div>

      <div className="results-actions">
        <button
          onClick={async () => {
            try {
              const { data } = await api.post("/race/continue");
              onContinue(data);
            } catch (err) {
              console.error(err);
            }
          }}
        >
          Continue to Next Race {"->"}
        </button>
      </div>
    </div>
  );
}
