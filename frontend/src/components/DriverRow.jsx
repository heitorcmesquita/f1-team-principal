import LogoImg from "./LogoImg";
import { getTeamColor } from "../utils/teamData";

function tyreColor(tyre) {
  switch (tyre?.toLowerCase()) {
    case "macio":
    case "soft":
      return "#e10600";

    case "medio":
    case "medium":
      return "#ffd500";

    case "duro":
    case "hard":
      return "#ffffff";

    case "intermediario":
    case "intermediate":
      return "#39d353";

    case "chuva":
    case "wet":
      return "#0096ff";

    default:
      return "#888";
  }
}

function formatTyre(tyre) {
  switch (tyre?.toLowerCase()) {
    case "macio":
      return "Soft";
    case "medio":
      return "Medium";
    case "duro":
      return "Hard";
    case "intermediario":
      return "Intermediate";
    case "chuva":
      return "Wet";
    default:
      return tyre || "-";
  }
}

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

function PositionDelta({ delta }) {
  if (!delta) return <span style={{ color: "#6b7280" }}>-</span>;

  const isUp = delta > 0;
  return (
    <span style={{ color: isUp ? "#22c55e" : "#ef4444", fontWeight: 800 }}>
      {isUp ? "▲" : "▼"} {Math.abs(delta)}
    </span>
  );
}

export default function DriverRow({ driver, highlight, isLeader }) {
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
      <td style={{ fontWeight: 700, color: '#fff' }}>{driver.position}</td>
      <td>
        <PositionDelta delta={driver.position_delta} />
      </td>

      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <LogoImg teamName={driver.team} size="20px" alt={driver.team} />
          <strong style={{ color: '#fff' }}>{driver.driver}</strong>
        </div>
      </td>

      <td style={{ color: '#9ca3af' }}>{driver.team}</td>

      <td>
        <span
          style={{
            display: "inline-block",
            width: 12,
            height: 12,
            borderRadius: "50%",
            backgroundColor: tyreColor(driver.tyre),
            marginRight: 8,
            border: "1px solid rgba(255,255,255,0.2)"
          }}
        />

        {formatTyre(driver.tyre)}
      </td>

      <td>{driver.tyre_age}</td>

      <td style={{ fontWeight: driver.gap === 0 ? 700 : 500, color: driver.gap === 0 ? '#ffd500' : '#9ca3af' }}>{formatGap(driver.gap)}</td>

      <td>{formatLap(driver.last_lap)}</td>

      <td style={{ color: driver.pit_stops > 0 ? '#f3f4f6' : '#6b7280', fontWeight: 600 }}>
        {driver.pit_stops || 0}
      </td>
    </tr>
  );
}
