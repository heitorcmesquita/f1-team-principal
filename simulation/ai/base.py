"""Decision engine contracts for the pluggable AI strategy module.

Two concrete engines implement the protocol: the heuristic engine (the
historical in-game AI, moved verbatim) and the LLM engine (an OpenAI-compatible
chat-completions call). Engines are interchangeable via ``simulation.ai.factory``
and the active one is recorded in ``race_state["ai_engine"]`` as a plain
``"heuristic" | "api"`` string so saves stay JSON-safe and secret-free.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol, runtime_checkable


@dataclass
class PitDecision:
    """One AI driver's tyre/pit decision for the current lap.

    - ``action`` is ``"pit"`` or ``"stay"``.
    - ``tyre`` is the normalized compound to fit when pitting.
    - ``reason`` is a human-readable string that flows into the event feed.
    """

    driver: str
    action: str = "stay"
    tyre: Optional[str] = None
    reason: Optional[str] = None


@runtime_checkable
class DecisionEngine(Protocol):
    """An engine that decides AI pit/tyre strategy for a race (and, optionally,
    second qualifying runs)."""

    name: str

    def pit_plan(self, race_state: dict, events: list, rng=None) -> List[PitDecision]:
        """Decide and *apply* pit/stay for every AI driver this lap.

        Engines mutate ``race_state`` (``pit_pending`` on driver states) and
        append human-readable messages to ``events`` — exactly how the
        historical heuristic applied its decisions — and return the decisions
        they took. Implementations must never raise.
        """
        ...

    def decide_run2(self, qual: dict, driver_name: str) -> bool:
        """Whether an AI driver should leave the pits for a second qualifying run."""
        ...