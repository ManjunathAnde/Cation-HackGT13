# Build Checkpoints — Cation (HackGT 13, Impiricus challenge)

Each checkpoint is a small, working step. A checkpoint is **done** only when its test passes and its
notes are written.

## Process rules

- **Document as you go:** add 3–5 lines to `docs/PROGRESS.md` per checkpoint (what works, how to test,
  known issues) plus one screenshot in `docs/screenshots/` for anything visual.
- **Never commit secrets:** `.env`, `secrets/`, and service-account keys stay out of git (public repo).
- **If a checkpoint stalls past its timebox, cut scope** rather than blocking the next one.

## MVP scope

| Must (demo fails without it) | Should (strong demo) | Could (only if ahead) |
| --- | --- | --- |
| Onboarding → cards → replies → scores | Live Gemini/Groq explorer | Real RCS on an Android phone |
| RCS mockup with Yes / Not interested | Mock ION panel changing its pick | ClinicalTrials.gov cards |
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

**Test:** in `http://localhost:8000/docs`: POST /onboard → (GET /next-card → POST /reply) ×3 →
POST /topic-reply (yes) → GET /metrics shows score 72 → GET /vault?q=kidney returns 2 items.
Error cases: unknown doctor → 404; replying to a card twice → 400.
**Document:** example request/response for /reply in README.

## Checkpoint 6 — Doctor portal: onboarding
**Goal:** Dr. Patel's profile is created from the UI.

**Test:** fill the form → GET /profile/dr_patel shows the three starting topics at 1.
**Document:** screenshot.

## Checkpoint 7 — RCS mockup
**Goal:** cards arrive in a phone-shaped UI; buttons drive the loop.

**Test:** tap through all three cards and the expansion offer from the UI; scores and ION pick
change after each tap.
**Document:** screenshot of each card; short screen recording (backup for the demo video).

## Checkpoint 8 — Vault
**Test:** after the path, vault shows 2 saved items; search "kidney" finds them; search "xyz" finds none.
**Document:** screenshot.

## Checkpoint 9 — Metrics page
**Test:** timeline lists every event in order; topic scores match the terminal run; engagement
score 72, reply rate 100%, yes rate 67%, 1 topic added, 2 saved.
**Document:** screenshot. ← **MVP complete here.**

## Checkpoint 10 — Live LLM with failover
**Test:** with Gemini key → timeline shows `by: gemini`. Remove Gemini key → `by: groq`.
Remove both → `by: cache`. Demo path unchanged in all three.
**Document:** note which models were used.

## Checkpoint 11 — Mock ION panel
**Test:** panel shows "General update for endocrinology (specialty only)" before any taps and
"kidney outcomes content (top score 3 from replies)" after the path.
**Document:** screenshot for the pitch slide.

## Parallel track — Real RCS (friend, 2-hour timebox)
- **R1:** agent created, test Android phone accepted tester invite
- **R2:** one rich card with two buttons arrives on the phone
- **R3:** tapping a button reaches the backend through the webhook and calls the same reply logic

**Test:** tap "Yes" on the phone → metrics page timeline shows the reply.
**If stalled at the timebox:** stop; demo with the mockup.

## Checkpoint 12 — Demo freeze
**Goal:** nothing new, only reliability.
- [ ] All external data cached; demo works with Wi-Fi off (except live LLM, which falls back to cache)
- [ ] 3 full dry runs, timed; 2-minute video recorded
- [ ] Devpost writeup, architecture slide, roadmap slide

**Test:** a teammate who didn't build the UI runs the whole demo from a fresh clone.