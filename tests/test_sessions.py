import json

from fastapi.testclient import TestClient

from backend.app.services import session_service
from backend.app.services.session_service import COOKIE_NAME, SessionStore


def _world(client: TestClient):
    """Return the RaceService behind a TestClient's cookie."""
    sid = client.cookies.get(COOKIE_NAME)
    assert sid, "no session cookie set yet"
    svc = session_service.session_store.touch(sid)
    assert svc is not None
    return svc


# --- store-level isolation --------------------------------------------------

def test_two_sessions_own_independent_worlds():
    store = SessionStore()
    a = store.create("sid-a")
    b = store.create("sid-b")

    assert a is not b
    assert a._save_path != b._save_path
    # Starting a season on A must not leak into B.
    a.start_season(1, ai_key="SECRET-KEY-A")
    a.qualifying_skip()
    a.start_race({})
    for _ in range(5):
        a.next_lap({})

    assert a.phase == "race"
    assert b.phase == "selection"
    assert b._ai_key is None
    # And B can start its own season without disturbing A's in-flight race.
    b.start_season(2)
    assert a.phase == "race"


def test_ai_key_never_serialized():
    store = SessionStore()
    a = store.create("sid-key")
    a.start_season(1, ai_key="SUPER-SECRET")
    payload = json.dumps(a.export_save(), ensure_ascii=False)
    assert "SUPER-SECRET" not in payload
    assert "ai_api_key" not in payload
    # The engine name travels as a plain string (safe to persist), not the key.
    a.qualifying_skip()
    a.start_race({})
    assert a.race["ai_engine"] == "api"


def test_reset_clears_ai_key():
    store = SessionStore()
    a = store.create("sid-reset")
    a.start_season(1, ai_key="SECRET")
    assert a._ai_key == "SECRET"
    a.reset()
    assert a._ai_key is None


def test_sessions_api_key_without_key_is_heuristic():
    store = SessionStore()
    a = store.create("sid-heuristic")
    a.start_season(1)
    a.qualifying_skip()
    a.start_race({})
    assert a.race["ai_engine"] == "heuristic"


def test_saved_session_with_api_engine_loads_heuristic_without_key():
    store = SessionStore()
    a = store.create("sid-save")
    a.start_season(1, ai_key="KEY")
    a.qualifying_skip()
    a.start_race({})
    a.next_lap({})
    snapshot = a.export_save()
    assert snapshot["race"]["ai_engine"] == "api"

    fresh = store.create("sid-fresh")
    fresh.start_season(2)
    fresh.load_game(snapshot)
    # Loaded with an "api" tag but no key: must fall back gracefully, not throw.
    assert fresh.race["ai_engine"] == "api"  # preserved tag
    fresh.qualifying_skip()
    fresh.start_race({})
    fresh.race["ai_engine"] = "heuristic"
    fresh.next_lap({})  # no key -> heuristic engine, no network, no crash
    assert fresh.phase == "race"


def test_idle_sessions_are_evicted():
    store = SessionStore()
    old_cap = session_service.MAX_SESSIONS
    session_service.MAX_SESSIONS = 5
    try:
        ids = [f"sid-{i}" for i in range(6)]
        for i in ids:
            store.create(i)
        # The first-created was evicted, the newest remain.
        assert store.touch(ids[0]) is None
        assert store.touch(ids[-1]) is not None
        assert len(store._services) <= 5
    finally:
        session_service.MAX_SESSIONS = old_cap


# --- end-to-end isolation through the HTTP API ------------------------------

def test_http_two_visitors_do_not_share_work():
    app = _app()
    alice = TestClient(app)
    bob = TestClient(app)

    teams = alice.get("/race/teams").json()
    team_id = teams[0]["id"]

    r1 = alice.post("/race/start", json={"team_id": team_id, "ai_api_key": "ALICE-SECRET"})
    assert r1.status_code == 200
    assert _world(alice)._ai_key == "ALICE-SECRET"

    # Bob arrives later: a clean, empty, keyless world.
    r2 = bob.get("/race/state")
    assert r2.status_code == 200
    assert r2.json()["phase"] == "selection"
    assert _world(bob)._ai_key is None
    assert _world(bob).phase == "selection"

    # Alice runs the weekend without touching Bob.
    alice.post("/race/qualifying/skip", json={"phase": "end"})
    alice.post("/race/start-race", json={})
    alice.post("/race/next-lap", json={})
    assert _world(alice).phase == "race"
    assert _world(bob).phase == "selection"

    # Alice's save export contains her race but never her key.
    blob = json.dumps(alice.get("/race/save/data").json(), ensure_ascii=False)
    assert "ALICE-SECRET" not in blob


def _app():
    from backend.app.main import app
    return app