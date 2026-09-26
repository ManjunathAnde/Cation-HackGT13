# Cation
## Working agreement — follow strictly

Scope
- Implement ONLY what the current task asks. No extra features, refactors, styling,
  dependencies, or "improvements" unless explicitly requested.
- If something outside scope seems necessary, stop and ask. Do not do it.
- Never change the card format, endpoint names, or scoring rules without asking.
- Before every code change, we do an evaluation where you saw tell me how things are, what are they getting changed and scoped for errors

Two-phase process for every task
- Phase 1 (PLAN): write a plan only. Do not create or edit any files.
  The plan must list: files to create/modify, what each change does, new dependencies
  (if any), how it will be tested, and any assumptions or open questions.
- Wait for explicit approval ("approved" or a revised plan) before Phase 2.
- Phase 2 (IMPLEMENT): implement exactly the approved plan. If you must deviate,
  stop and explain why before continuing.

Implementation report (end of every Phase 2)
1. Files changed (created / modified / deleted)
2. What was implemented, mapped to each plan item
3. Test run: exact commands and their actual output
4. Deviations from the plan (or "none")
5. Known issues or TODOs
6. Suggested commit message

Context
- Read CLAUDE.md and docs/PROGRESS.md at the start of every session.
- After each approved task, update docs/PROGRESS.md: checkpoint, what works, how to test,
  known issues. Keep entries short.
- Keep CLAUDE.md's "Current state" section accurate.

Hygiene
- Never commit or print secrets. Keys live only in backend/.env.
- Small, readable functions. Plain code makes every decision; the LLM only suggests.


HackGT 13 project for the **Impiricus challenge**.

Cation is an agent that sends doctors research cards over RCS, learns from their
**Yes** / **Not interested** replies, and feeds the learned interest profile to
Impiricus's ION platform. For the demo, ION is simulated.

## Stack

- **Frontend:** React + Vite, in `/frontend` (dev server on http://localhost:5173)
- **Backend:** FastAPI, in `/backend` (Python 3.10+, dev server on http://localhost:8000)
- **Config:** `python-dotenv` loads `backend/.env`. See `.env.example` for the keys.
- **Storage:** in-memory only for the demo. No database. Restarting the backend wipes state.

## Card format

Every research card sent to a doctor has this shape:

```json
{
  "id": "string",
  "title": "string",
  "summary": "string",
  "source": "string",
  "link": "string",
  "topics": ["string"],
  "claims": ["string"],
  "kind": "string"
}
```

## Core rule

**The LLM only suggests. Plain code makes every decision.**

LLM output (summaries, topic tags, suggested next cards) is treated as a suggestion.
Plain, deterministic code decides what gets sent, how the profile is updated, and
what goes to ION.

## Status

Checkpoint 2: scaffold only. The backend exposes `GET /health`, and the frontend shows
whether the backend is reachable. No features yet.

## Secrets

Never commit `.env`, `secrets/`, or any `*service-account*.json`. These are gitignored.
