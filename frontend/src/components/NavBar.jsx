const TABS = [
  { key: "race", label: "Race" },
  { key: "championship", label: "Championship" },
  { key: "calendar", label: "Calendar" },
  { key: "settings", label: "Settings" },
];

export default function NavBar({ view, setView }) {
  return (
    <nav className="nav-bar" aria-label="Main navigation">
      <button className="nav-menu-btn" aria-label="Open menu" aria-expanded="true">
        ☰
      </button>
      <div className="nav-menu">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`nav-tab ${view === t.key ? "active" : ""}`}
            onClick={() => setView(t.key)}
            aria-current={view === t.key ? "page" : undefined}
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
