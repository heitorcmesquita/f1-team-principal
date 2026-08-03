import DriverRow from "./DriverRow";

export default function RaceTable({ drivers, playerTeam }) {
  const leader = drivers && drivers.length > 0 ? drivers[0].driver : null;

  // Fastest lap among valid times
  let fastestDriver = null;
  let fastestTime = Infinity;
  (drivers || []).forEach((d) => {
    if (d.last_lap && d.last_lap > 0 && d.last_lap < fastestTime) {
      fastestTime = d.last_lap;
      fastestDriver = d.driver;
    }
  });

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
              isFastest={driver.driver === fastestDriver}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
