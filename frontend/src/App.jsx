import { useEffect, useMemo, useRef, useState } from "react";
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
import Championship from "./components/Championship";
import Calendar from "./components/Calendar";
import Settings from "./components/Settings";
import SeasonFinished from "./components/SeasonFinished";
import LapNav from "./components/LapNav";

import "./App.css";

const SAVE_KEY = "f1manager.save";

function App() {
  const [race, setRace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [teams, setTeams] = useState([]);
  const [playerTeam, setPlayerTeam] = useState(null);
  const [view, setView] = useState("race");
  const [toasts, setToasts] = useState([]);
  const [choices, setChoices] = useState({});
  const [confirm, setConfirm] = useState("");
  const [sending, setSending] = useState(false);

  // Client-side lap history. Each engine "next lap" pushes a snapshot here so
  // the user can rewind (and re-forward) without calling the game engine again.
  const [history, setHistory] = useState([]);
  // -1 means "live" (latest state); otherwise an index into `history`.
  const [viewIndex, setViewIndex] = useState(-1);

  const live = viewIndex === -1;
  const displayed = live ? race : history[viewIndex] || race;

  const playerDrivers = useMemo(() => {
    if (!race || !race.classification) return [];
    if (playerTeam && playerTeam.drivers) {
      return playerTeam.drivers.map((d) => d.name);
    }
    const myDrivers = race.classification
      .filter((d) => d.team === (playerTeam && playerTeam.name))
      .map((d) => d.driver);
    if (myDrivers.length) return myDrivers;
    if (race.classification.length) {
      const team = race.classification.find(Boolean).team;
      return race.classification.filter((d) => d.team === team).slice(0, 2).map((d) => d.driver);
    }
    return [];
  }, [race, playerTeam]);

  useEffect(() => {
    const init = {};
    playerDrivers.forEach((d) => (init[d] = "Stay Out"));
    setChoices(init);
  }, [playerDrivers.join("|")]);

  function setChoice(driver, value) {
    setChoices((s) => ({ ...s, [driver]: value }));
    setConfirm("");
  }

  // Keep this player's game in their own browser so every visitor has their
  // own world instead of sharing one server-side game.
  async function persistSave() {
    try {
      const { data } = await api.get("/race/save/data");
      localStorage.setItem(SAVE_KEY, JSON.stringify(data));
    } catch (err) {
      console.error(err);
    }
  }

  async function nextLap(commands) {
    try {
      const { data } = await api.post("/race/next-lap", commands || {});
      applyRace(data);
      return data;
    } catch (err) {
      console.error(err);
      return null;
    }
  }

  async function handleNextLap() {
    const payload = {};
    for (const d of playerDrivers) {
      const choice = choices[d] || "Stay Out";
      if (choice && choice !== "Stay Out") payload[d] = choice;
    }
    setSending(true);
    const next = await nextLap(payload);
    setSending(false);
    if (next) {
      // Store the new state as a navigable snapshot and jump to live.
      setHistory((h) => [...h, next]);
      setViewIndex(-1);
    }
    const sent = Object.keys(payload);
    if (next && sent.length) {
      setConfirm(`Lap ${next.lap || race.lap} sent: ` + sent.map((d) => `${d} → ${payload[d]}`).join(", "));
    }
    const reset = {};
    playerDrivers.forEach((d) => (reset[d] = "Stay Out"));
    setChoices(reset);
  }

  function goPrev() {
    if (viewIndex === -1) {
      if (history.length > 0) setViewIndex(history.length - 1);
    } else if (viewIndex > 0) {
      setViewIndex(viewIndex - 1);
    }
  }

  function goNext() {
    if (viewIndex !== -1) {
      // Navigate the stored history — no engine call.
      if (viewIndex < history.length - 1) setViewIndex(viewIndex + 1);
      else setViewIndex(-1); // back to live
      return;
    }
    // At live: advance the race engine (only if the race can still advance).
    if (displayed && displayed.phase === "race" && !displayed.finished) {
      handleNextLap();
    }
  }

  // Used by the header "Next Lap" button: behind → move forward in history,
  // at live → call the engine.
  function advanceLap() {
    if (viewIndex !== -1) {
      goNext();
      return;
    }
    if (displayed && displayed.phase === "race" && !displayed.finished) {
      handleNextLap();
    }
  }

  function handleContinue(nextState) {
    setRace(nextState);
    setHistory([]);
    setViewIndex(-1);
    persistSave();
  }

  async function handleGameLoaded() {
    // A save was restored on the backend — re-fetch everything from scratch.
    setHistory([]);
    setViewIndex(-1);
    await loadInitial();
    setView("race");
  }

  const navRef = useRef(null);
  useEffect(() => {
    // Keep the latest navigation closures/handlers available to the
    // keydown listener, which is only subscribed once.
    navRef.current = { goPrev, goNext, view, viewIndex, race, history };
  });

  useEffect(() => {
    function onKey(e) {
      const ref = navRef.current;
      if (!ref) return;
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      const tag = (e.target.tagName || "").toUpperCase();
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (ref.view !== "race") return;
      const d = ref.viewIndex === -1 ? ref.race : ref.history[ref.viewIndex];
      if (!d || d.phase !== "race") return;
      e.preventDefault();
      if (e.key === "ArrowLeft") ref.goPrev();
      else ref.goNext();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const prevSC = useRef(null);
  const prevWeather = useRef(null);
  const toastSeq = useRef(0);

  function pushToast(kind, title, body) {
    const id = ++toastSeq.current;
    setToasts((t) => [...t, { id, kind, title, body }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 8000);
  }

  function applyRace(data) {
    if (!data) return;
    setRace(data);
    persistSave();
    const sc = Boolean(data.safety_car);
    const weather = data.weather || null;
    if (prevSC.current !== null && sc && !prevSC.current) {
      pushToast("sc", "Safety Car Deployed", "Track speed restricted — this is a free pit window.");
    }
    if (prevWeather.current !== null && weather && weather !== prevWeather.current) {
      pushToast("weather", "Weather Change", `Conditions changed to ${weather}. All cars pit together next lap — choose your tyres.`);
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
      setHistory([]);
      setViewIndex(-1);
      const team = teams.find((t) => t.id === teamId || String(t.id) === String(teamId)) || null;
      setPlayerTeam(team);
      setView("race");
    } catch (err) {
      console.error(err);
      const msg = err?.response?.data?.detail || err?.message || "Failed to start season";
      alert(msg);
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

  async function handleNewSeason() {
    localStorage.removeItem(SAVE_KEY);
    try {
      await api.post("/race/reset");
    } catch (err) {
      console.error(err);
    }
    setPlayerTeam(null);
    setRace(null);
    setHistory([]);
    setViewIndex(-1);
    setView("race");
  }

  useEffect(() => {
    async function boot() {
      // Restore this visitor's own save (kept in the browser), so everyone
      // plays their own world. First-time visitors get a fresh server state
      // rather than inheriting the previous player's game.
      const saved = localStorage.getItem(SAVE_KEY);
      try {
        if (saved) {
          await api.post("/race/load", JSON.parse(saved));
        } else {
          await api.post("/race/reset");
        }
      } catch (err) {
        console.error(err);
        localStorage.removeItem(SAVE_KEY);
      }
      await loadInitial();
    }
    boot();
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner" aria-hidden="true"></div>
        <span>Loading...</span>
      </div>
    );
  }

  // Season complete ceremony
  if (race && race.season_finished && playerTeam) {
    return (
      <div className="app">
      <RaceHeader race={race} playerTeam={playerTeam} onNextLap={handleNextLap} sending={sending} view={view} setView={setView} />
        <SeasonFinished onNewSeason={handleNewSeason} />
        <Toasts toasts={toasts} />
      </div>
    );
  }

  // Team selection / main menu
  if (!race || !race.race_name) {
    return (
      <div className="app">
        <TeamSelection teams={teams} onStart={startSeason} />
      </div>
    );
  }

  const showRaceChrome = view === "race";

  return (
    <div className="app">
      <RaceHeader race={displayed} playerTeam={playerTeam} onNextLap={advanceLap} sending={sending} view={view} setView={setView} />

      {!showRaceChrome ? (
        <>
          {view === "championship" && <Championship playerTeam={playerTeam} />}
          {view === "calendar" && <Calendar />}
          {view === "settings" && <Settings playerTeam={playerTeam} onLoaded={handleGameLoaded} />}
        </>
      ) : race.phase === "qualifying" ? (
        <Qualifying race={race} playerTeam={playerTeam} onTick={qualiTick} onSkip={qualiSkip} />
      ) : race.phase === "tyre_selection" ? (
        <TyreSelection race={race} playerTeam={playerTeam} onStartRace={startRace} />
      ) : (
        <>
          {displayed.safety_car && (
            <div className="sc-alert-banner" role="alert">
              ⚠️ <strong>SAFETY CAR DEPLOYED</strong> — Track Speed Restricted · Gaps Preserved This Lap
            </div>
          )}
          {displayed.red_flag && (
            <div className="rf-alert-banner" role="alert">
              🚩 <strong>RED FLAG STOPPAGE</strong> — Race Suspended Following Incident
            </div>
          )}

          <LapNav
            displayed={displayed}
            live={live}
            canPrev={viewIndex === -1 ? history.length > 0 : viewIndex > 0}
            canNext={viewIndex === -1 ? !displayed.finished && displayed.phase === "race" : true}
            onPrev={goPrev}
            onNext={goNext}
            onLive={() => setViewIndex(-1)}
          />

          {displayed.finished && live ? (
            <ResultsScreen race={displayed} teams={teams} playerTeam={playerTeam} onContinue={handleContinue} />
          ) : (
            <div className="content">
              <div className="left-panel">
                <RaceTable drivers={displayed.classification} playerTeam={playerTeam} />
                <EventLog events={displayed.events} />
              </div>
              <div className="right-panel">
                <StrategyPanel
                  race={displayed}
                  choices={choices}
                  onChoice={setChoice}
                  confirm={confirm}
                  playerDrivers={playerDrivers}
                  disabled={!live}
                />
                <TelemetryChart race={displayed} playerTeam={playerTeam} />
              </div>
            </div>
          )}
        </>
      )}

      <Toasts toasts={toasts} />
    </div>
  );
}

function Toasts({ toasts }) {
  if (!toasts.length) return null;
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <strong>{t.title}</strong>
          <span>{t.body}</span>
        </div>
      ))}
    </div>
  );
}

export default App;
