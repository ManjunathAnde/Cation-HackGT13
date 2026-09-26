# Build Checkpoints — Cation (HackGT 13, Impiricus challenge)

Each checkpoint is a small, working step. A checkpoint is **done** only when its test passes and its
notes are written.

**Build order:** 1–5 → 10a → 10b → 6 → 7 → 8 → 9 → 11 → 12. Checkpoints keep their numbers; sections
below follow the build order.

## Process rules

- **Document as you go:** add 3–5 lines to `docs/PROGRESS.md` per checkpoint (what works, how to test,
  known issues) plus one screenshot in `docs/screenshots/` for anything visual.
- **Never commit secrets:** `.env`, `secrets/`, and service-account keys stay out of git (public repo).
- **If a checkpoint stalls past its timebox, cut scope** rather than blocking the next one.

## MVP scope

| Must (demo fails without it) | Should (strong demo) | Could (only if ahead) |
| --- | --- | --- |
| Onboarding → cards → replies → scores | Live Gemini/Groq explorer | ClinicalTrials.gov cards |
| Phone page thread with Yes / Not interested | Mock ION panel changing its pick | |
| Real DailyMed label + real PubMed studies (cached) | Score line chart (needs approval) | Other 4 doctors + brand view |
| Vault with search | Guard block shown once | Deployment to a public URL |
| Metrics: timeline, scores, engagement score | Weight-management block shown | |

---

## Checkpoint 1 — Repo setup
**Goal:** local and remote git connected; team can clone.
- [ ] Repo `ManjunathAnde/Cation-HackGT13` has at least one commit on `main`
- [ ] All teammates added as collaborators and invites accepted
- [ ] `.gitignore` in place before any `.env` exists

**Test:** a teammate runs `git clone` and `git push` on a test branch successfully.
**Document:** README exists; repo URL shared with team.

## Checkpoint 2 — Scaffold running
**Goal:** backend and frontend start on every laptop.
- [ ] Scaffold unzipped into repo root, committed, pushed
- [ ] Each person: venv + `pip install -r requirements.txt`, `npm install`
- [ ] `backend/.env` created from `.env.example` (keys shared privately)

**Test:** `http://localhost:8000/health` returns `{"ok": true}`; `http://localhost:5173` shows
"backend connected ✓" — on every teammate's machine.
**Document:** any OS-specific setup fixes added to README.

## Checkpoint 3 — Core loop (terminal)
**Goal:** the intelligence layer runs Dr. Patel's full path with no UI, using the §5.5 placeholder data.
- [ ] `backend/data/cache.json`, `backend/data/label.json`, `backend/app/core.py`, `backend/app/demo_run.py`

**Test:** `python -m app.demo_run` from `backend/` replays blueprint.md §12, prints each step,
and ends with plain `assert` checks on every §12 value, printing `DEMO PATH OK`.
**Document:** paste the terminal output into docs/PROGRESS.md.

## Checkpoint 4 — Real data
**Goal:** replace placeholders with real, verified content.
- [ ] Verbatim Ozempic kidney-indication sentence from DailyMed pasted into `cache.json` (label card
      `claims`) and `label.json`, replacing the PLACEHOLDER sentence
- [ ] `python -m app.fetch_label` and `python -m app.fetch_studies` run (email set); titles reviewed;
      1–2 good studies kept per topic

**Test:** `demo_run` still follows the same path with real titles; guard says "Claims match label."
Change one character in the label claim → guard blocks it → change it back.
**Document:** list the PubMed IDs used and the DailyMed label version/date.

## Checkpoint 5 — API
**Goal:** every step works over HTTP.

**Test:** in `http://localhost:8000/docs`: POST /onboard → (POST /send → POST /reply) ×3 →
POST /topic-reply (yes) → GET /metrics shows score 72 → GET /vault?q=kidney returns 2 items →
GET /inbox returns the full thread (3 answered cards + 1 answered offer, `active` null).
Error cases: unknown doctor → 404; replying to a card twice → 400; POST /send while a card is
unanswered → 400.
**Document:** example request/response for /reply in README.

## Checkpoint 10a — Live LLM with failover
**Goal:** the explorer's related-topic suggestions come from Gemini → Groq → fixed fallback; plain code
still decides what is skipped, blocked, or offered.

**Test:** `python -m app.llm_check` shows `by: gemini`, then `groq` (Gemini key hidden in memory), then
`fallback` (both hidden), each with valid suggestions. `demo_run` and `api_check` pass with
`LLM_MODE=off`. With `LLM_MODE=live`, a replay of the demo shows `topic_offered` with `by: gemini` in
/metrics, and any off-label suggestion is logged as `topic_blocked`.
**Document:** note which models were used.

## Checkpoint 10b — Redis cache in front of provider calls
**Goal:** cache LLM suggestions in Redis in front of the provider calls, without changing
`suggest_related`'s callers; `by` gains `redis`. The Redis client dependency needs approval (not in
blueprint §13).

## Checkpoint 6 — Doctor portal: onboarding
**Goal:** Dr. Patel's profile is created from the UI.

**Test:** fill the form → GET /profile/dr_patel shows the three starting topics at 1.
**Document:** screenshot.

## Checkpoint 7 — Phone page
**Goal:** cards arrive as a conversation thread on a phone-shaped page; buttons drive the loop.
The operator view has only the "Send next card" button here; the metrics and ION panels join it
in Checkpoints 9 and 11.

**Test:** operator clicks Send → the card appears at the bottom of the phone thread within 2 seconds →
tapping a button shows the reply under that card and disables its buttons; GET /metrics/dr_patel
reflects the reply. Earlier messages stay visible.
**Document:** screenshot of each card; short screen recording (backup for the demo video).

## Checkpoint 8 — Vault
**Test:** after the path, vault shows 2 saved items; search "kidney" finds them; search "xyz" finds none.
**Document:** screenshot.

## Checkpoint 9 — Metrics page
**Test:** timeline lists every event in order; topic scores match the terminal run; engagement
score 72, reply rate 100%, yes rate 67%, 1 topic added, 2 saved.
**Document:** screenshot. ← **MVP complete here.**

## Checkpoint 11 — Mock ION panel
**Test:** panel shows "General update for endocrinology (specialty only)" before any taps and
"kidney outcomes content (top score 3 from replies)" after the path.
**Document:** screenshot for the pitch slide.

## Checkpoint 12 — Demo freeze
**Goal:** nothing new, only reliability.
- [ ] All external data cached; demo works with Wi-Fi off (except live LLM, which falls back to a fixed list)
- [ ] 3 full dry runs, timed; 2-minute video recorded
- [ ] Devpost writeup, architecture slide, roadmap slide

**Test:** a teammate who didn't build the UI runs the whole demo from a fresh clone.