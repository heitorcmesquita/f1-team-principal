import DriverRow from "./DriverRow";

export default function RaceTable({ drivers, playerTeam }) {
  const leader = drivers && drivers.length > 0 ? drivers[0].driver : null;
  
  return (
    <div className="race-table-container">
      <table className="race-table">
        <thead>
          <tr>
            <th>Pos</th>
            <th>Change</th>
            <th>Driver</th>
            <th>Team</th>
            <th>Tyre</th>
            <th>Age</th>
            <th>Gap</th>
            <th>Last Lap</th>
            <th>Pits</th>
          </tr>
        </thead>

        <tbody>
          {drivers.map((driver) => (
            <DriverRow
              key={driver.driver}
              driver={driver}
              highlight={playerTeam && playerTeam.name === driver.team}
              isLeader={driver.driver === leader}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
