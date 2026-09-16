"""Engine resolution.

The active engine is chosen from the session's API key: a key present means the
LLM engine, otherwise the heuristic. The factory never throws and never touches
the network — it only constructs the engine object (the API call happens later,
inside a batched, throttled lap). Quality decisions stay out of the save game
except for the plain engine-name string stored in ``race_state["ai_engine"]``.
"""

from typing import Optional

from simulation.ai.base import DecisionEngine
from simulation.ai.heuristic import HeuristicEngine

_heuristic = HeuristicEngine()


def engine_name(ai_key: Optional[str] = None) -> str:
    """The engine label to record in the save ('' or None -> heuristic)."""
    return "api" if ai_key else "heuristic"


def resolve_engine(ai_key: Optional[str] = None) -> DecisionEngine:
    """Return the engine for this session. Never raises; falls back to heuristic."""
    if not ai_key:
        # api.py is imported lazily so the httpx dependency is only loaded when
        # an LLM engine is actually requested (keeps /health and boot free of
        # any network/API machinery).
        return _heuristic
    from simulation.ai.api import ApiEngine

    return ApiEngine(api_key=ai_key)