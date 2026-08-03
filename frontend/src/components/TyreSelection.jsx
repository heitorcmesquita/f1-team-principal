import { useEffect, useMemo, useState } from "react";
import LogoImg from "./LogoImg";
import { tyreColor } from "../utils/tyres";

const TYRE_OPTIONS = ["Soft", "Medium", "Hard", "Intermediate", "Wet"];

function fmtLap(t) {
  if (t == null) return "-";
  const m = Math.floor(t / 60);
  const s = (t - m * 60).toFixed(3);
  return `${m}:${String(s).padStart(6, "0")}`;
}

export default function TyreSelection({ race, playerTeam, onStartRace }) {
  const grid = race.grid || [];
  const [choices, setChoices] = useState({});
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const playerDrivers = useMemo(() => {
    if (playerTeam && playerTeam.drivers) {
      return playerTeam.drivers.map((d) => d.name);
    }
    if (playerTeam && playerTeam.name) {
      return (race.grid || []).filter((g) => g.team === playerTeam.name).map((g) => g.driver);
    }
    return [];
  }, [playerTeam, race.grid]);

  function pickDriverTyre(name, value) {
    setError("");
    setChoices((s) => ({ ...s, [name]: value }));
  }

  useEffect(() => {
    if (playerDrivers.length === 0) return;
    setChoices((s) => {
      const next = { ...s };
      playerDrivers.forEach((d) => {
        if (!next[d]) next[d] = "Soft";
      });
      return next;
    });
  }, [playerDrivers.join("|")]);

  async function handleStart() {
    if (playerDrivers.some((d) => !choices[d])) {
      setError("Choose a starting tyre for every driver.");
      return;
    }
    const payload = {};
    playerDrivers.forEach((d) => {
      payload[d] = choices[d];
    });
    setStarting(true);
    setError("");
    await onStartRace(payload);
  }

  return (
    <div className="tyre-select-screen">
      <div className="tyre-select-body">
        <div className="tyre-select-grid">
          <table className="tyre-grid-table">
            <thead>
              <tr>
                <th>Pos</th>
                <th>Driver</th>
                <th>Team</th>
                <th>Quali Time</th>
              </tr>
            </thead>
            <tbody>
              {grid.map((g) => (
                <tr key={g.driver} className={playerDrivers.includes(g.driver) ? "tyre-player-row" : ""}>
                  <td className="quali-pos">{g.position}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <LogoImg teamName={g.team} size="22px" alt={g.team} />
                      <strong>{g.driver}</strong>
                    </div>
                  </td>
                  <td className="quali-team">{g.team}</td>
                  <td className="quali-time">{fmtLap(g.best_lap)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="tyre-select-side">
          <div className="tyre-picker">
            <h3>Your drivers</h3>
            {playerDrivers.length === 0 ? (
              <p className="empty-events">No drivers found for your team.</p>
            ) : (
              playerDrivers.map((name) => (
                <div className="tyre-picker-row" key={name}>
                  <strong>{name}</strong>
                  <select
                    value={choices[name] || "Soft"}
                    onChange={(e) => pickDriverTyre(name, e.target.value)}
                  >
                    {TYRE_OPTIONS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  {choices[name] && (
                    <span
                      className="tyre-dot tyre-dot-large"
                      style={{ background: tyreColor(choices[name]) }}
                      title={choices[name]}
                      aria-hidden="true"
                    ></span>
                  )}
                </div>
              ))
            )}
          </div>

          {error && <p className="tyre-error">{error}</p>}

          <div className="tyre-select-actions">
            <button className="next-lap-btn" onClick={handleStart} disabled={starting || playerDrivers.length === 0}>
              {starting ? "Starting Race..." : "Start Race"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
