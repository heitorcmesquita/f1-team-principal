import { useEffect, useState } from "react";
import { api } from "../api";
import LogoImg from "./LogoImg";
import { getCircuitFlagPath } from "../utils/circuitFlags";

export default function SeasonFinished({ onNewSeason }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.get("/race/standings"), api.get("/race/calendar")])
      .then(([s, c]) => mounted && setData({ standings: s.data, calendar: c.data }))
      .catch(console.error);
    return () => (mounted = false);
  }, []);

  if (!data) return <div className="loading-panel">Calculating championship...</div>;

  const dStandings = data.standings.standings || [];
  const cStandings = data.standings.constructor_standings || [];
  const champion = dStandings[0];
  const cChampion = cStandings[0];
  const results = data.standings.season_results || [];

  return (
    <div className="season-finished">
      <div className="season-finished-hero">
        <h2>Season Complete</h2>
        <p className="season-finished-sub">
          {results.length} rounds completed — congratulations to the champions.
        </p>
      </div>

      <div className="season-champions">
        <div className="champion-card">
          <span className="champion-label">Drivers Champion</span>
          {champion && (
            <>
              <LogoImg teamName={champion.team} size="40px" alt={champion.team} />
              <span className="champion-name">{champion.driver}</span>
              <span className="champion-team">{champion.team}</span>
              <span className="champion-points">{champion.points} pts</span>
            </>
          )}
        </div>
        <div className="champion-card">
          <span className="champion-label">Constructors Champion</span>
          {cChampion && (
            <>
              <LogoImg teamName={cChampion.team} size="40px" alt={cChampion.team} />
              <span className="champion-name">{cChampion.team}</span>
              <span className="champion-points">{cChampion.points} pts</span>
            </>
          )}
        </div>
      </div>

      <div className="standings-grid season-final">
        <section className="panel-card">
          <h3>Final Drivers Championship</h3>
          <table className="shared-table">
            <thead>
              <tr>
                <th scope="col">Pos</th>
                <th scope="col">Driver</th>
                <th scope="col">Team</th>
                <th scope="col" className="num">Pts</th>
              </tr>
            </thead>
            <tbody>
              {dStandings.slice(0, 10).map((s, i) => (
                <tr key={s.driver}>
                  <td className="num">{i + 1}</td>
                  <td>
                    <div className="cell-driver">
                      <LogoImg teamName={s.team} size="20px" alt={s.team} />
                      <strong>{s.driver}</strong>
                    </div>
                  </td>
                  <td>{s.team}</td>
                  <td className="num pts">{s.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel-card">
          <h3>Final Constructors Championship</h3>
          <table className="shared-table">
            <thead>
              <tr>
                <th scope="col">Pos</th>
                <th scope="col">Team</th>
                <th scope="col" className="num">Pts</th>
              </tr>
            </thead>
            <tbody>
              {cStandings.map((s, i) => (
                <tr key={s.team}>
                  <td className="num">{i + 1}</td>
                  <td>
                    <div className="cell-driver">
                      <LogoImg teamName={s.team} size="20px" alt={s.team} />
                      <strong>{s.team}</strong>
                    </div>
                  </td>
                  <td className="num pts">{s.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      {results.length > 0 && (
        <section className="panel-card season-results-card">
          <h3>Season Results</h3>
          <div className="season-results">
            {results.map((r, i) => {
              const winner = r.classification && r.classification[0];
              return (
                <div key={i} className="season-result-row">
                  <span className="season-result-round">
                    {getCircuitFlagPath(r.circuit) && (
                      <img
                        src={getCircuitFlagPath(r.circuit)}
                        alt={`${r.circuit} flag`}
                        className="calendar-flag"
                      />
                    )}
                    R{i + 1} · {r.circuit}
                  </span>
                  <span className="season-result-winner">
                    {winner ? `${winner.driver} (${winner.team})` : "-"}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <div className="season-finished-actions">
        <button className="next-lap-btn" onClick={onNewSeason}>
          Start New Season
        </button>
      </div>
    </div>
  );
}
