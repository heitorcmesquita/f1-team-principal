import { formatTyre, tyreColor } from "../utils/tyres";

const OPTIONS = ["Stay Out", "Soft", "Medium", "Hard", "Intermediate", "Wet"];

export default function StrategyPanel({ race, choices, onChoice, confirm, playerDrivers, disabled }) {
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
          const cur = state.tyre || "";
          const age = state.tyre_age != null ? state.tyre_age : null;
          const planned = choices[name] && choices[name] !== "Stay Out" ? choices[name] : null;
          return (
            <div key={name} className="strategy-driver">
              <div className="sd-header">
                <strong>{name}</strong>
                <span className="sd-pos">#{state.position || "-"}</span>
              </div>

              <div className="sd-tyre">
                {cur ? (
                  <>
                    <span
                      className="tyre-dot"
                      style={{ background: tyreColor(cur) }}
                      aria-hidden="true"
                    ></span>
                    <span className="sd-tyre-label">
                      On {formatTyre(cur)}
                      {age != null ? ` · ${age} lap${age === 1 ? "" : "s"}` : ""}
                    </span>
                  </>
                ) : (
                  <span className="sd-tyre-label sd-tyre-empty">No tyre data</span>
                )}
                {planned && (
                  <span className="sd-plan-badge">→ {planned}</span>
                )}
              </div>

              <select value={choices[name] || "Stay Out"} onChange={(e) => onChoice(name, e.target.value)} disabled={disabled}>
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

      {disabled && <p className="strategy-locked">Locked — viewing a past lap.</p>}
      {confirm && <p className="strategy-confirm">✓ {confirm}</p>}
    </div>
  );
}
