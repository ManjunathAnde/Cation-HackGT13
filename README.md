# Cation

**The intelligence layer for Impiricus ION.** Cation sends doctors one useful research read at a time, learns from every *Yes* / *Not interested* tap, and turns those replies into first-party engagement data.

Built at **HackGT 13** for the Impiricus challenge: *Invent the Next Way We Engage HCPs.*

![How Cation works](docs/cation_workflow.png)

---

## What it does

- **Doctor onboarding:** specialty, the conditions their patients face, and interests become a personal topic profile (practice-level only, no patient data).
- **One useful read at a time:** peer-reviewed PubMed studies and FDA-label-exact brand updates arrive automatically on a phone-style brief.
- **Every tap is a signal:** *Yes* → +1 and saved to the vault; *Not interested* → −1; a topic at −2 is muted.
- **Adaptive picking:** at most 2 cards in a row per topic. After 2 *Yes* taps, AI (Gemini, with Groq as failover) chooses a related topic, and its paper comes next, marked *"Related to what you liked."*
- **Impiricus console:** a 0–100 engagement score, topic scores, a full event timeline, and ION's next best action, updating live.
- **Compliant by design:** a **brand lane** (FDA-label-exact, approved uses only) and a **clinical lane** (neutral research). Off-label topics are blocked and routed to medical information.

Two demo doctors run on the same engine: **Dr. Patel** (endocrinology, brand + clinical lanes) and **Dr. Evan** (dermatology, clinical lane only).

## Architecture

```
  DOCTOR · phone brief                      IMPIRICUS · console
  onboard · read · Yes/No · vault           engagement · timeline · ION
        │   ▲                                          ▲
   taps │   │ next card (auto-sent)                    │ live metrics
        ▼   │                                          │
┌─────────────── CATION INTELLIGENCE LAYER · FastAPI ───────────────┐
│   Topic scores ──► Picker ──► Compliance guard ──► Deliver card   │
│   (+1 / −1)         │          (FDA-label exact,                  │
│      ▲              ▼           off-label blocked)                │
│   Reply events   AI topic choice at switch points                 │
│                  Gemini ──► Groq ──► rule-based fallback          │
│                  (chooses only from code-validated topics)        │
└──────────┬─────────────────────────────────────────┬──────────────┘
           │ reads                                   │ exposes
           ▼                                         ▼
   RESEARCH LIBRARY                          ION-READY API
   Brand lane · Clinical lane                /profile · /events
   PubMed (NIH MeSH) · DailyMed labels       first-party signals
```

**Principle:** the AI chooses only among options the code has already validated; the code builds the options, checks the choice, and falls back if the AI fails.

## The math

| | Rule |
|---|---|
| Topic score | starts at 1; *Yes* +1, *Not interested* −1, no reply −0.25; muted at ≤ −2 |
| Picker | FDA label first (brand lane); ≤ 2 cards in a row per topic; switch on run limit, 2-*Yes* streak, or topic exhausted |
| Engagement | `E = clip₀₋₁₀₀( 40·R + 40·Y + min(5·A, 20) − 10·M )` |

`R` = reply rate · `Y` = yes rate · `A` = topics added via AI suggestions · `M` = topics muted. Sending more messages can't raise `E`; only relevant ones can.

## Quick start

**Prerequisites:** Python 3.10+, Node.js 18+

**1. Configure** (runs without any keys: the AI then uses its rule-based fallback)

```bash
cp .env.example backend/.env
```

| Variable | Purpose | Default |
|---|---|---|
| `LLM_MODE` | `live` uses Gemini/Groq; `off` uses the rule-based fallback | `off` |
| `AUTO_SEND` | send the next card automatically after each answer | `on` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | primary AI provider | — |
| `GROQ_API_KEY`, `GROQ_MODEL` | failover AI provider | — |
| `REDIS_URL` | Upstash Redis for cached AI suggestions | — |
| `NCBI_EMAIL` | contact email for the PubMed fetch scripts | — |

Never commit `backend/.env`.

**2. Backend** → http://localhost:8000 (API docs at `/docs`)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   ·   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Check: http://localhost:8000/health → `{"ok": true}`

**3. Frontend** → http://localhost:5173 (second terminal)

```bash
cd frontend
npm install
npm run dev
```

## Run the demo

1. Open the **console**: http://localhost:5173/console
2. Pick **Dr. Patel** → **Reset demo** → **Open Dr. Patel's phone ↗**
3. Pick **Dr. Evan** → **Reset demo** → **Open Dr. Evan's phone ↗**
4. Answer cards on each phone and watch the console: scores, engagement, timeline, and ION update live.

New doctors can onboard at http://localhost:5173/phone/onboard.

> The backend keeps doctor data in memory. After a restart, press **Reset demo** for each doctor.

## Tests

From `backend/` (the LLM runs in `off` mode for deterministic results):

```bash
python -m app.demo_run      # Dr. Patel's full path in-process  → DEMO PATH OK
python -m app.derm_check    # Dr. Evan (dermatology) end to end → DERM CHECK OK
python -m app.api_check     # full path over HTTP (backend with LLM_MODE=off) → API PATH OK
python -m app.llm_check     # live Gemini → Groq → fallback check (needs keys)
```

## Project structure

```
backend/
  app/            core.py (intelligence loop) · llm.py (AI + failover) · main.py (API)
                  fetch_label.py · fetch_studies.py (research pipeline) · checks
  data/           cache.json (research library) · label.json (FDA label) · specialties.json
frontend/src/     pages (console, onboard, brief, vault) · components · api.js
docs/             CHECKPOINTS.md · design mockups · screenshots
blueprint.md      full specification
```

## Data and compliance

- **Sources:** PubMed (NIH E-utilities, MeSH topics; randomized trials, systematic reviews, meta-analyses) and DailyMed (FDA labels). Titles, journals, years, and links only; no abstracts.
- **Curated library:** every study was human-reviewed for on-label relevance; the fetch pipeline is built to refresh the library on a schedule.
- **Guardrails:** brand claims must match the FDA label word for word; off-label topics are blocked; no patient data is collected; the AI never writes medical content.

## Roadmap

- Connect `/profile` and `/events` to the real Impiricus ION
- Scheduled library refresh with automatic compliance screening
- Any specialty, with conditions validated against NIH MeSH
- Real RCS delivery and frequency-based scheduling
- Persistent storage and a brand-level dashboard

## Built with

Python · FastAPI · Pydantic · React · Vite · Gemini API · Groq · Upstash Redis · PubMed E-utilities · NIH MeSH · DailyMed · Claude Code

See [`blueprint.md`](blueprint.md) for the full specification and [`docs/CHECKPOINTS.md`](docs/CHECKPOINTS.md) for the build history.