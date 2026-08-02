import { useEffect, useRef } from "react";

function formatEventMessage(message) {
  return String(message)
    .replace(/\bmacio\b/gi, "Soft")
    .replace(/\bmedio\b/gi, "Medium")
    .replace(/\bduro\b/gi, "Hard")
    .replace(/\bintermediario\b/gi, "Intermediate")
    .replace(/\bchuva\b/gi, "Wet");
}

export default function EventLog({ events }) {
  const bodyRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to newest event
    const el = bodyRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [events]);

  // group events by lap
  const grouped = (events || []).reduce((acc, ev) => {
    (acc[ev.lap] = acc[ev.lap] || []).push(ev.message);
    return acc;
  }, {});

  const laps = Object.keys(grouped).map((k) => Number(k)).sort((a, b) => a - b);

  return (
    <div className="event-log">

      <div className="event-log-header">
        <h2>Race Events</h2>
      </div>

      <div className="event-log-body" ref={bodyRef}>

        {laps.length === 0 ? (
          <p className="empty-events">No events yet.</p>
        ) : (
          laps.map((lap) => (
            <div key={lap} className="event-lap-group">
              <div className="event-lap-title">Lap {lap}</div>
              {grouped[lap].map((msg, i) => (
                <div key={i} className="event-item">
                  <span className="event-message">{formatEventMessage(msg)}</span>
                </div>
              ))}
            </div>
          ))
        )}

      </div>

    </div>
  );
}
