import { useEffect, useMemo, useState } from "react";

const OPTIONS = ["Stay Out", "Soft", "Medium", "Hard", "Intermediate", "Wet"];

export default function StrategyPanel({ race, playerTeam, onNextLap }) {
  const [choices, setChoices] = useState({});

  const playerDrivers = useMemo(() => {
    if (!race || !race.classification) return [];
    if (playerTeam && playerTeam.drivers) {
      return playerTeam.drivers.map((d) => d.name);
    }
    const myDrivers = race.classification.filter((d) => d.team === (playerTeam && playerTeam.name)).map((d) => d.driver);
    if (myDrivers.length) return myDrivers;
    if (race.classification.length) {
      const team = race.classification.find(Boolean).team;
      return race.classification.filter((d) => d.team === team).slice(0, 2).map((d) => d.driver);
    }
    return [];
  }, [race, playerTeam]);

  useEffect(() => {
    const init = {};
    playerDrivers.forEach((d) => (init[d] = "Stay Out"));
    setChoices(init);
  }, [playerDrivers.join("|")]);

  function setChoice(driver, value) {
    setChoices((s) => ({ ...s, [driver]: value }));
  }

  async function handleNextLap() {
    const payload = {};
    for (const d of playerDrivers) {
      const choice = choices[d] || "Stay Out";
      if (choice && choice !== "Stay Out") payload[d] = choice;
    }

    await onNextLap(payload);

    const reset = {};
    playerDrivers.forEach((d) => (reset[d] = "Stay Out"));
    setChoices(reset);
  }

  if (!playerDrivers || playerDrivers.length === 0) {
    return (
      <div className="strategy-panel">
        <h3>Strategy</h3>
        <p>No drivers found for your team yet.</p>
      </div>
    );
  }

  return (
    <div className="strategy-panel">
      <h3>Strategy</h3>

      <div className="strategy-drivers">
        {playerDrivers.map((name) => {
          const state = race.classification.find((d) => d.driver === name) || {};
          return (
            <div key={name} className="strategy-driver">
              <div className="sd-header">
                <strong>{name}</strong>
                <span className="sd-pos">#{state.position || "-"}</span>
              </div>

              <select value={choices[name] || "Stay Out"} onChange={(e) => setChoice(name, e.target.value)}>
                {OPTIONS.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>

      <button className="next-lap-btn strategy-next" onClick={handleNextLap}>
        Next Lap
      </button>
    </div>
  );
}
