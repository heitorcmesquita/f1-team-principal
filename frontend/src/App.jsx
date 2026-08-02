import { useEffect, useRef, useState } from "react";
import { api } from "./api";

import RaceHeader from "./components/RaceHeader";
import RaceTable from "./components/RaceTable";
import EventLog from "./components/EventLog";
import TeamSelection from "./components/TeamSelection";
import StrategyPanel from "./components/StrategyPanel";
import ResultsScreen from "./components/ResultsScreen";
import Qualifying from "./components/Qualifying";
import TyreSelection from "./components/TyreSelection";
import TelemetryChart from "./components/TelemetryChart";

import "./App.css";

function App() {
  const [race, setRace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [teams, setTeams] = useState([]);
  const [playerTeam, setPlayerTeam] = useState(null);
  const [popup, setPopup] = useState(null);

  const prevSC = useRef(null);
  const prevWeather = useRef(null);

  function applyRace(data) {
    if (!data) return;
    setRace(data);
    const sc = Boolean(data.safety_car);
    const weather = data.weather || null;
    if (prevSC.current !== null && sc && !prevSC.current) {
      setPopup({
        title: "Safety Car Deployed",
        body: "Track speed restricted and gaps preserved. This is a free pit window — bring your drivers in.",
      });
    }
    if (prevWeather.current !== null && weather && weather !== prevWeather.current) {
      setPopup({
        title: "Weather Change",
        body: `Conditions changed to ${weather}. All cars stay out for one lap, then every team pits together — prepare your tyre choice.`,
      });
    }
    prevSC.current = sc;
    prevWeather.current = weather;
  }

  async function loadInitial() {
    try {
      const [stateResp, teamsResp] = await Promise.all([api.get("/race/state"), api.get("/race/teams")]);
      prevSC.current = Boolean(stateResp.data?.safety_car);
      prevWeather.current = stateResp.data?.weather || null;
      setRace(stateResp.data);
      setTeams(teamsResp.data);
      const teamId = stateResp.data?.player_team_id;
      if (teamId != null) {
        const team = teamsResp.data.find((t) => t.id === teamId || String(t.id) === String(teamId)) || null;
        setPlayerTeam(team);
      } else {
        setPlayerTeam(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function startSeason(teamId) {
    try {
      const { data } = await api.post("/race/start", { team_id: teamId });
      applyRace(data);
      const team = teams.find((t) => t.id === teamId || String(t.id) === String(teamId)) || null;
      setPlayerTeam(team);
    } catch (err) {
      console.error(err);
      const msg = err?.response?.data?.detail || err?.message || "Failed to start season";
      alert(msg);
    }
  }

  async function nextLap(commands) {
    try {
      const { data } = await api.post("/race/next-lap", commands || {});
      applyRace(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function qualiTick(seconds = 10) {
    try {
      const { data } = await api.post("/race/qualifying/tick", { seconds });
      applyRace(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function qualiSkip(phase) {
    try {
      const { data } = await api.post("/race/qualifying/skip", phase ? { phase } : {});
      applyRace(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function startRace(startingTyres) {
    try {
      const { data } = await api.post("/race/start-race", startingTyres || {});
      applyRace(data);
    } catch (err) {
      console.error(err);
      const msg = err?.response?.data?.detail || err?.message || "Failed to start race";
      alert(msg);
    }
  }

  useEffect(() => {
    loadInitial();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!race || !race.race_name) {
    return (
      <div className="app">
        <TeamSelection teams={teams} onStart={startSeason} />
      </div>
    );
  }

  return (
    <div className="app">
      <RaceHeader race={race} playerTeam={playerTeam} />

      {race.phase === "qualifying" ? (
        <Qualifying race={race} playerTeam={playerTeam} onTick={qualiTick} onSkip={qualiSkip} />
      ) : race.phase === "tyre_selection" ? (
        <TyreSelection race={race} playerTeam={playerTeam} onStartRace={startRace} />
      ) : (
        <>
          {race.safety_car && (
            <div className="sc-alert-banner">
              ⚠️ <strong>SAFETY CAR DEPLOYED</strong> — Track Speed Restricted · Gaps Preserved This Lap
            </div>
          )}
          {race.red_flag && (
            <div className="rf-alert-banner">
              🚩 <strong>RED FLAG STOPPAGE</strong> — Race Suspended Following Incident
            </div>
          )}

          {race.finished ? (
            <ResultsScreen race={race} teams={teams} onContinue={(nextState) => setRace(nextState)} />
          ) : (
            <div className="content">
              <div className="left-panel">
                <RaceTable drivers={race.classification} playerTeam={playerTeam} />
              </div>
              <div className="right-panel">
                <StrategyPanel race={race} playerTeam={playerTeam} onNextLap={nextLap} />
                <TelemetryChart race={race} playerTeam={playerTeam} />
                <EventLog events={race.events} />
              </div>
            </div>
          )}
        </>
      )}

      {popup && (
        <div className="popup-overlay">
          <div className="popup-modal">
            <h3>{popup.title}</h3>
            <p>{popup.body}</p>
            <button className="popup-ok-btn" onClick={() => setPopup(null)}>
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
