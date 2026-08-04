# F1 Team Principal

A browser-based single-player Formula 1 team management game. Pick your team,
run qualifying, manage your drivers' tyres and race strategy, and fight for the
world championship across a full season — directly in the browser, for free.

## Quick start (local development)

**Backend (FastAPI)**

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --port 8000
```

**Frontend (React + Vite)**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies API calls to the
backend on port 8000.

**Tests**

```bash
python -m pytest
```

## How the game works

- **Team selection** — pick one of the 11 teams; you control its two drivers.
- **Qualifying** — advance through Q1/Q2/Q3 (or skip) to set the grid.
- **Tyre selection** — choose starting tyres for each of your drivers.
- **Race** — call laps, issue pit-stop commands (Soft/Medium/Hard/Intermediate/
  Wet), react to safety cars and weather changes, and watch the classification
  evolve. Arrow keys rewind/forward through the laps you've already raced.
- **Championship** — standings, constructors, results and calendar for the whole
  season.

## Saves

Your game is saved **automatically in your browser** (localStorage) after every
move, so each player has their own independent world — no accounts, no server
database. Use **Settings → My Save (Browser)** to export a backup file or import
one on another device.

## Architecture

The project is split into a **Python simulation/API backend** and a **React
single-page frontend** that talk over a small REST API. There is no database:
the game state lives in memory and is persisted per-player via JSON.

```
f1-manager/
├── backend/                      # FastAPI backend
│   └── app/
│       ├── main.py               # FastAPI app: CORS, /health, serves the built SPA
│       ├── api/race.py           # REST endpoints (state, teams, start, next-lap, save/load…)
│       ├── schemas/race_state.py # Pydantic response models (RaceState, DriverState, RaceEvent)
│       └── services/
│           ├── race_service.py     # RaceService: weekend phase machine + singleton
│           ├── season_service.py   # season standings, results, calendar
│           ├── analytics_service.py# lap-by-lap telemetry history
│           ├── save_service.py     # tagged-JSON (de)serialization of the object graph
│           └── state_builder.py    # builds the classification / driver state payloads
├── simulation/                   # game engine (pure logic, no HTTP)
│   ├── race.py                   # create_race, run_lap, weather, safety car, final classification
│   └── qualifying.py             # qualifying session simulation (Q1/Q2/Q3)
├── game/                         # legacy terminal (CLI) version — entry point is root main.py
├── data/static/                  # drivers.json, teams.json, circuits.json
├── models.py / utils.py          # Driver/Team/Circuit dataclasses + shared data loader
├── frontend/                     # React + Vite single-page app
│   ├── src/App.jsx               # top-level state, lap history/rewind, auto-save to localStorage
│   ├── src/api.js                # axios client (dev proxy → /api, prod → same-origin /race)
│   └── src/components/           # UI panels: RaceTable, StrategyPanel, Qualifying,
│                                 # TyreSelection, TelemetryChart, Championship, Settings, …
├── tests/                        # pytest suite (20 tests)
├── render.yaml                   # Render deploy blueprint
└── requirements.txt              # Python dependencies
```

**Request flow.** The React app calls e.g. `POST /race/next-lap`;
`api/race.py` delegates to the `RaceService` singleton, which advances
`simulation/race.py` by one lap, records events and analytics, and returns a
fresh `RaceState`. A fixed `random.Random` instance drives the simulation.

**State & saves.** The whole game lives in memory as a graph of dicts plus
dataclass references (`Driver`, `Team`, `Circuit`). `save_service.py` converts
that graph to tagged JSON (e.g. `{"$type": "driver", ...}`) so it can be
written to a file or shipped to the browser. The frontend keeps each player's
save in `localStorage` and restores it via `POST /race/load` on page load — so
every visitor has their own independent world and the server holds no per-user
data.

## Deploying

The repo includes `render.yaml` (Render free web service). On Render:

1. Dashboard → **New +** → **Blueprint**.
2. Connect the GitHub repo and select the branch to deploy.
3. Render reads `render.yaml`, installs the Python deps from `requirements.txt`
   and starts `uvicorn backend.app.main:app` serving both the API and the built
   frontend from the same origin.

Free-tier note: the service sleeps after ~15 minutes idle, so the first request
after a pause can take about a minute to respond.

## Legal & Disclaimer

### Proprietary code — no commercial reuse

The source code in this repository is **proprietary** and the property of the
author. **All rights are reserved.** It is shared for reference only and must
**not** be reused, copied, modified, redistributed, or incorporated into other
projects — and in particular it may **not be used commercially** or sold — without
the author's prior written permission. The code is not open source and is **not**
licensed under MIT, GPL, or any permissive license. See `LICENSE` for the exact
terms. If you would like to license or reuse any part of this code, contact the
author.

### Fan-project & trademark disclaimer

This project is an **unofficial, non-commercial fan project**. It is a personal
hobby project and is not sold, monetized, or otherwise operated for profit.

- **Not affiliated or endorsed.** This project is not affiliated with, endorsed
  by, or sponsored by Formula One World Championship Limited, the Fédération
  Internationale de l'Automobile (FIA), Liberty Media, or any Formula 1 team,
  driver, sponsor, or rights holder.
- **Trademarks.** "Formula 1", "F1", team names, driver names, and all other
  marks, logos, and trade dress used in this project are the property of their
  respective owners. Their use here is for identification and reference only
  within a fan project and does not imply any sponsorship or endorsement.
- **Third-party assets.** Any logos or images that belong to their respective
  owners are used without permission and solely for illustrative, non-commercial
  purposes. If you are a rights holder and would like a logo or name removed,
  please open an issue on this repository and it will be removed promptly.
- **No commercial use.** This software is provided free of charge for
  entertainment purposes. It must not be sold, bundled with paid products, or
  used to generate revenue (including via ads or donations) without first
  clearing rights with the relevant rights holders.
- **No warranties.** The software is provided "as is", without warranty of any
  kind. See the project license for details.

This disclaimer does not constitute legal advice. If you plan to use this
project commercially or in any public capacity, consult a qualified attorney.
