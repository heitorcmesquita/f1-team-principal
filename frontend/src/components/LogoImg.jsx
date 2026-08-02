import { getTeamLogo } from "../utils/teamData";

export default function LogoImg({ teamName, size = "32px", alt = "" }) {
  return (
    <img
      src={getTeamLogo(teamName)}
      alt={alt || teamName}
      style={{
        width: size,
        height: size,
        objectFit: "contain",
        marginRight: "8px",
      }}
      onError={(e) => {
        e.target.src = "/logos/f1.png";
      }}
    />
  );
}
