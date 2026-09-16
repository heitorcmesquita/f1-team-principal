"""Pluggable AI decision engines for race/tyre strategy.

- ``HeuristicEngine`` — the historical in-game AI, kept verbatim as the
  reference implementation and the automatic fallback.
- ``ApiEngine`` — an OpenAI-compatible chat-completions client (Groq, Gemini,
  OpenRouter, Cerebras…), batched once per lap, throttled to plausible laps,
  falling back to the heuristic on any failure.
- ``resolve_engine()`` in :mod:`simulation.ai.factory` chooses between them.
"""

from simulation.ai.base import DecisionEngine, PitDecision
from simulation.ai.heuristic import HeuristicEngine
from simulation.ai.factory import engine_name, resolve_engine

__all__ = [
    "DecisionEngine",
    "HeuristicEngine",
    "PitDecision",
    "engine_name",
    "resolve_engine",
]

__version__ = "1.0.0"