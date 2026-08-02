import React from "react";
import LogoImg from "./LogoImg";

export default function TeamSelection({ teams, onStart }) {
  if (!teams || teams.length === 0) return <p>No teams available.</p>;

  return (
    <div className="team-selection">
      <h2>Choose Your Team</h2>
      <div className="team-grid">
        {teams.map((t) => (
          <div className="team-card" key={t.id}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
              <LogoImg teamName={t.name} size="48px" alt={t.name} />
              <h3 style={{ margin: 0, color: "#ffffff" }}>{t.name}</h3>
            </div>

            <div className="team-stats">
              <div>
                <div style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Engine</div>
                <div style={{ fontWeight: 700, fontSize: '14px' }}>{t.engine}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Aero</div>
                <div style={{ fontWeight: 700, fontSize: '14px' }}>{t.aerodynamics}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reliability</div>
                <div style={{ fontWeight: 700, fontSize: '14px' }}>{t.reliability}</div>
              </div>
            </div>

            <div className="team-drivers">
              <strong>Drivers</strong>
              <ul>
                {t.drivers.map((d) => (
                  <li key={d.name}>{d.name}</li>
                ))}
              </ul>
            </div>

            <div className="team-actions">
              <button onClick={() => { console.log('TeamSelection: start clicked', t.id); if (onStart) onStart(t.id); }}>Start Season</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
