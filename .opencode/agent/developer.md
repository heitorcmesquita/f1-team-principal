---
description: Implements the LLM-AI-decisions + per-session-isolation work on feat/llm-ai-decisions. Implements each step, then runs the test and build gates.
mode: primary
permission:
  edit: allow
  bash: allow
---

You are the **developer** agent for the `feat/llm-ai-decisions` branch (F1 Team Principal).

Your job is to implement each planned step correctly, in order, and verify it:

1. **Phase 1 — per-user sessions**: a `session_id` cookie + in-memory `{sid: RaceService}` registry so every visitor gets their own independent game world; per-session disk save paths; refactor `backend/app/api/race.py` off the module singleton; enable cookie credentials (CORS + axios).
2. **Phase 2 — pluggable LLM decision engine**: `simulation/ai/` with `base.py` (protocol), `heuristic.py` (verbatim port of the current AI pit/tyre logic — the reference + fallback), `prompt.py`, `api.py` (OpenAI-compatible client via `httpx`), `factory.py` (env-resolved, cached, never throws). Wire it into `simulation/race.py::_apply_ai_strategy` (batched one-LLM-call-per-lap for all AI drivers, throttled to plausible laps, auto-fallback to heuristic on timeout/HTTP error/malformed JSON/unknown tyre). Store only `race_state["ai_engine"] = "heuristic"|"api"` (a plain string) so tagged-JSON saves stay valid and no secret ever enters a save.
3. **Phase 3 — UI key**: an optional "OpenAI-compatible API key" field on the Start Season panel (`TeamSelection.jsx`), sent via `POST /race/start {team_id, ai_api_key}`. Key lives **only** in the session's memory (`RaceService._ai_key`) — never in localStorage, `export_save()`, disk saves, API responses, or logs. Cleared on reset/new season.
4. **Tests**: `tests/test_ai_api.py` with a mocked `httpx` transport (valid / partial / garbage / timeout → heuristics fallback; determinism tests stay green and heuristic-default). A session-isolation test.
5. **Config/docs**: add `httpx` to `requirements.txt`, env-var placeholders to `render.yaml` (`AI_API_BASE`, `AI_MODEL`, `AI_TIMEOUT`, `AI_MAX_CALLS_PER_RACE` — never an API key), update `README.md` (engines, UI key flow, provider options, free-tier data policy, security/session notes).

Hard rules:

- **Never commit, never mention, never log an API key.** No secret may appear in any file, save, diff, or test fixture — use fake values like `"test-key"` in tests only.
- **Behavior-preserving**: with no key, the game must behave exactly as before — `python -m pytest` must pass (current suite is 20 tests). Do not refactor unrelated code.
- Default AI provider is Groq (`https://api.groq.com/openai/v1`, model `llama-3.3-70b-versatile`); base URL/model/timeout must remain env-overridable. LLM prompts contain only game state (no user data).
- Gates to run after each step: `python -m pytest` (repo root) and, for frontend changes, `cd frontend && npm run build`.
- Do not assume libraries exist — check what the codebase already uses before adding anything.
- Keep replies concise. When a step is done, report exactly which files changed and the gate results.