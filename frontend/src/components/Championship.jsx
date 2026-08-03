import { useEffect, useState } from "react";
import { api } from "../api";
import LogoImg from "./LogoImg";

export default function Championship({ playerTeam }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let mounted = true;
    api
      .get("/race/standings")
      .then((resp) => mounted && setData(resp.data))
      .catch(console.error);
    return () => (mounted = false);
  }, []);

  if (!data) return <div className="loading-panel">Loading standings...</div>;

  const pTeam = playerTeam && playerTeam.name;

  return (
    <div className="shell-panel">
      <div className="shell-panel-head">
        <h2>Championship</h2>
        <span className="analytics-driver-count">Season in progress</span>
      </div>

      <div className="standings-grid">
        <section className="panel-card">
          <h3>Drivers Championship</h3>
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
              {(data.standings || []).map((s, i) => (
                <tr key={s.driver} className={s.team === pTeam ? "row-player" : ""}>
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
          <h3>Constructors Championship</h3>
          <table className="shared-table">
            <thead>
              <tr>
                <th scope="col">Pos</th>
                <th scope="col">Team</th>
                <th scope="col" className="num">Pts</th>
              </tr>
            </thead>
            <tbody>
              {(data.constructor_standings || []).map((s, i) => (
                <tr key={s.team} className={s.team === pTeam ? "row-player" : ""}>
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
    </div>
  );
}
