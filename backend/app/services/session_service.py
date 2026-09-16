"""Per-visitor session isolation.

The server is a single shared process with one heap; previously the API routed
every request to a module-level ``RaceService`` singleton, so all visitors
mutated the same game world. This module gives each browser its *own*
independent server-side section:

- a ``session_id`` cookie (unguessable, HttpOnly) identifies a visitor;
- ``SessionStore`` maps ``session_id`` -> a dedicated ``RaceService`` with its
  own on-disk save file (``data/saves/<session_id>.json``), so Save/Load and
  AI keys never cross between visitors;
- idle sessions are evicted when the store grows, keeping the free tier's heap
  bounded (Render restarts clear everything anyway).

A visitor's API key is held only on their own service (``RaceService._ai_key``)
in memory and is never serialized to saves or responses.

NOTE: isolation is per proceess. The Render blueprint runs a single uvicorn
worker, so the in-memory map is authoritative for the whole deployment; scaling
to multiple workers would require a shared session store.
"""

import secrets
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.app.services.race_service import RaceService

COOKIE_NAME = "f1_session"
# A long-lived cookie so a return visit (and reloads) keep the same section.
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
SAVES_ROOT = Path("data/saves")
MAX_SESSIONS = 256


class SessionStore:
    """Registry of active sessions: ``sid -> (RaceService, last_used_ts)``."""

    def __init__(self) -> None:
        self._services: Dict[str, Tuple[RaceService, float]] = {}
        self._lock = threading.Lock()

    def touch(self, session_id: str) -> Optional[RaceService]:
        """Return the session's service, refreshing its idle timestamp.

        Atomic (no separate ``has`` + ``get`` race): returns None if the
        session is unknown or was evicted, letting the caller mint a fresh
        world instead of crashing.
        """
        with self._lock:
            entry = self._services.get(session_id)
            if entry is None:
                return None
            service, _ = entry
            self._services[session_id] = (service, time.time())
            return service

    def create(self, session_id: str) -> RaceService:
        """Create and register a brand-new independent world for the visitor."""
        service = RaceService(save_path=SAVES_ROOT / f"{session_id}.json")
        with self._lock:
            self._services[session_id] = (service, time.time())
            self._evict_if_needed()
        return service

    def new_session_id(self) -> str:
        return secrets.token_urlsafe(32)

    def _evict_if_needed(self) -> None:
        while len(self._services) > MAX_SESSIONS:
            oldest = min(self._services.items(), key=lambda kv: kv[1][1])[0]
            svc, _ = self._services.pop(oldest)
            # Orphan the evicted world's on-disk save (the game was living in
            # this process's memory and is gone anyway); keeps the disk bounded.
            try:
                save = getattr(svc, "_save_path", None)
                if save is not None and save.exists():
                    save.unlink()
            except OSError:
                pass


# Shared by the FastAPI dependency in backend.app.api.race
session_store = SessionStore()