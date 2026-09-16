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
            <th className="col-pos">Pos</th>
            <th className="col-change"><span className="hdr-full">Change</span><span className="hdr-short">Chg</span></th>
            <th className="col-driver">Driver</th>
            <th className="col-team">Team</th>
            <th className="col-tyre">Tyre</th>
            <th className="col-age">Age</th>
            <th className="col-gap">Gap</th>
            <th className="col-last"><span className="hdr-full">Last Lap</span><span className="hdr-short">Time</span></th>
            <th className="col-pits">Pits</th>
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
