import LogoImg from "./LogoImg";
import { getTeamColor } from "../utils/teamData";
import { formatTyre, formatTyreShort, tyreColor } from "../utils/tyres";

function formatGap(gap) {
  if (gap === 0) return "Leader";
  if (gap == null) return "-";
  return `+${gap.toFixed(3)}`;
}

function formatLap(lap) {
  if (!lap) return "-";
  const minutes = Math.floor(lap / 60);
  const seconds = (lap % 60).toFixed(3).padStart(6, "0");
  return `${minutes}:${seconds}`;
}

function PositionDelta({ delta, reason }) {
  if (!delta) return <span style={{ color: "#6b7280" }}>-</span>;

  const isUp = delta > 0;
  const label = reason && reason !== "Unchanged" ? reason : "";
  return (
    <span
      style={{ color: isUp ? "#22c55e" : "#ef4444", fontWeight: 800 }}
      title={label}
    >
      {isUp ? "▲" : "▼"} {Math.abs(delta)}
    </span>
  );
}

export default function DriverRow({ driver, highlight, isLeader, isFastest }) {
  const teamColor = getTeamColor(driver.team);
  const highlightBg = highlight ? `${teamColor}1f` : 'transparent';
  const highlightBorder = highlight ? teamColor : 'transparent';

  return (
    <tr
      className={isLeader ? "leader-row" : highlight ? "highlight-driver" : ""}
      style={{
        backgroundColor: highlightBg,
        borderLeft: highlight ? `4px solid ${highlightBorder}` : 'none'
      }}
    >
      <td className="cell-pos" style={{ fontWeight: 700, color: '#fff' }}>{driver.position}</td>
      <td className="cell-change">
        <PositionDelta delta={driver.position_delta} reason={driver.position_delta_reason} />
      </td>

      <td className="cell-driver-wrap">
        <div className="race-driver-cell">
          <LogoImg teamName={driver.team} size="20px" alt={driver.team} />
          <strong style={{ color: '#fff' }}>{driver.driver}</strong>
        </div>
      </td>

      <td className="cell-team" style={{ color: '#9ca3af' }}>{driver.team}</td>

      <td className="cell-tyre">
        <span
          className="tyre-bullet"
          style={{
            backgroundColor: tyreColor(driver.tyre),
            border: "1px solid rgba(255,255,255,0.2)"
          }}
        />

        <span className="tyre-label tyre-label-full">{formatTyre(driver.tyre)}</span>
        <span className="tyre-label tyre-label-short">{formatTyreShort(driver.tyre)}</span>
      </td>

      <td className="cell-age">{driver.tyre_age}</td>

      <td className="cell-gap" style={{ fontWeight: driver.gap === 0 ? 700 : 500, color: driver.gap === 0 ? '#ffd500' : '#9ca3af' }}>{formatGap(driver.gap)}</td>

      <td className="cell-last">
        <span className="last-lap-cell">
          {formatLap(driver.last_lap)}
          {isFastest && <span className="fastest-chip" title="Fastest lap">FL</span>}
        </span>
      </td>

      <td className="cell-pits" style={{ color: driver.pit_stops > 0 ? '#f3f4f6' : '#6b7280', fontWeight: 600 }}>
        {driver.pit_stops || 0}
      </td>
    </tr>
  );
}
