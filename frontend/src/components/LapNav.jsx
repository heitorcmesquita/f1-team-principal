export default function LapNav({ displayed, live, canPrev, canNext, onPrev, onNext, onLive }) {
  const lap = displayed.lap || 0;
  const total = displayed.total_laps || 0;
  const finished = Boolean(displayed.finished);
  const label = finished ? `Final · Lap ${lap}/${total}` : `Lap ${lap}/${total}`;

  return (
    <div className={`lap-nav${live ? "" : " lap-nav-history"}`}>
      <button className="lap-nav-btn" onClick={onPrev} disabled={!canPrev} title="Previous lap (←)" aria-label="Previous lap">
        ◀
      </button>

      <div className="lap-nav-label">
        {!live && <span className="lap-nav-history-chip">HISTORY</span>}
        <span className="lap-nav-text">{label}</span>
        {!live && (
          <button className="lap-nav-live" onClick={onLive} title="Jump to live lap">
            ● Live
          </button>
        )}
      </div>

      <button className="lap-nav-btn" onClick={onNext} disabled={!canNext} title="Next lap (→)" aria-label="Next lap">
        ▶
      </button>
    </div>
  );
}
