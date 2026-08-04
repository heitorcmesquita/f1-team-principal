import { useState } from "react";

const TABS = [
  { key: "race", label: "Race" },
  { key: "championship", label: "Championship" },
  { key: "calendar", label: "Calendar" },
  { key: "settings", label: "Settings" },
];

export default function NavBar({ view, setView }) {
  const [open, setOpen] = useState(false);

  function select(key) {
    setView(key);
    setOpen(false);
  }

  return (
    <nav
      className={`nav-bar ${open ? "nav-open" : ""}`}
      aria-label="Main navigation"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
      }}
    >
      <button
        className="nav-menu-btn"
        aria-label="Open menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        ☰
      </button>
      <div className="nav-menu">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`nav-tab ${view === t.key ? "active" : ""}`}
            onClick={() => select(t.key)}
            aria-current={view === t.key ? "page" : undefined}
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
