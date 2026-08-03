import LogoImg from "./LogoImg";

const STATS = [
  { key: "engine", label: "Engine", color: "#fbbf24" },
  { key: "aerodynamics", label: "Aero", color: "#60a5fa" },
  { key: "reliability", label: "Reliability", color: "#39d353" },
];

function StatBar({ label, value, color }) {
  return (
    <div className="team-stat">
      <span className="team-stat-label">{label}</span>
      <div
        className="team-stat-bar"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} ${value}`}
      >
        <span className="team-stat-fill" style={{ width: `${value}%`, background: color }}></span>
      </div>
      <span className="team-stat-value">{value}</span>
    </div>
  );
}

export default function TeamSelection({ teams, onStart }) {
  if (!teams || teams.length === 0) return <p>No teams available.</p>;

  return (
    <div className="team-selection">
      <div className="team-selection-head">
        <h2>Choose Your Team</h2>
        <p className="team-selection-sub">Pick the team you will manage for the full season.</p>
      </div>

      <div className="team-grid">
        {teams.map((t) => (
          <div className="team-card" key={t.id} style={{ borderTop: `3px solid ${t.color_primary || "#e10600"}` }}>
            <div className="team-card-head">
              <LogoImg teamName={t.name} size="44px" alt={t.name} />
              <h3 style={{ margin: 0, color: "#ffffff" }}>{t.name}</h3>
            </div>

            <div className="team-stats">
              {STATS.map((s) => (
                <StatBar key={s.key} label={s.label} value={t[s.key]} color={s.color} />
              ))}
            </div>

            <div className="team-drivers">
              <strong>Drivers</strong>
              <ul>
                {t.drivers.map((d) => (
                  <li key={d.name} className="team-driver-row">
                    <span className="team-driver-name">
                      {d.country && (
                        <img
                          src={`/flags/${d.country}.svg`}
                          alt={`${d.country} flag`}
                          className="team-driver-flag"
                        />
                      )}
                      {d.name}
                    </span>
                    <span className="team-driver-talent">T{d.talent}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="team-actions">
              <button onClick={() => onStart(t.id)}>Start Season</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
