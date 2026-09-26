# Build Checkpoints — Cation (HackGT 13, Impiricus challenge)

Each checkpoint is a small, working step. A checkpoint is **done** only when its test passes and its
notes are written.

**Build order:** 1–5 → 10a → 10b → 6 → 7 → 8 → 9 → 11 → 12. Checkpoints keep their numbers; sections
below follow the build order. Checkpoint 7 (Impiricus console) absorbed the metrics page and the mock
ION panel; 8 is the Brief and 9 the Vault; 11 is now automatic sending.

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

**Test:** `http://localhost:8000/health` returns `{"ok": true}`; `http://localhost:5173` (redirects to
`/console`) — the console header shows "Backend connected" — on every teammate's machine.
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
**Goal:** cache the explorer's LLM suggestions in Upstash Redis in front of the providers
(Redis → Gemini → Groq → fallback), without changing `suggest_related`'s signature or callers;
`by` gains `redis`.

**Test:** `python -m app.llm_check` shows gemini (redis miss) → redis (hit) → gemini (redis
unreachable) → groq → fallback, then `LLM CHECK OK`. `demo_run` → `DEMO PATH OK`; `api_check`
against a server started with `LLM_MODE=off` → `API PATH OK` (neither touches Redis). Live server:
replay the demo (onboard → send/reply ×3) → `topic_offered` with `by: gemini`; re-onboard and replay →
`by: redis`, with a faster third /reply. The Upstash Data Browser shows a key starting with
`cation:explorer:v1:`. No key, token, or Redis password appears in any output or file.
**Document:** the third /reply's response time for both replays.

## Checkpoint 6 — Doctor portal: onboarding
**Goal:** Dr. Patel's profile is created from the UI.

**Test:** fill the form → GET /profile/dr_patel shows the three starting topics at 1.
**Document:** screenshot.

## Checkpoint 7 — Impiricus console
**Goal:** the Impiricus/brand side at `/console` (`/` redirects there): header with the backend
indicator, demo controls (Reset demo, open Dr. Patel's phone), "Send next card" with a status line,
the ION panel (simulated), the metrics (engagement score, rates, topics added, muted, saved, current
scores) and the event timeline. Polls every 2 seconds. Absorbs the former metrics page and mock ION panel.

**Test:** Reset demo → "Ready to send" → Send → "Waiting for Dr. Patel's reply to: Ozempic label:
kidney outcomes indication", Send disabled. Answering through the API updates status, metrics, ION and
timeline within ~2 s without a reload. After the full path: engagement 72 "High signal", reply 100%,
yes 67%, 1 topic added, 0 muted, 2 saved; kidney outcomes 3 first; ION "kidney outcomes content (top
score 3 from replies)" (before any replies: "General update for endocrinology (specialty only)"); the
weight management row carries the "Compliance safeguard" tag. Stopping the backend shows "Backend not
running" and "reconnecting…" without clearing panels; restarting recovers without a reload.
**Document:** screenshot for the pitch slide.

## Checkpoint 8 — Brief (phone thread)
**Goal:** cards arrive as a conversation thread on a phone-shaped page at `/phone/brief` (`/phone`
redirects there); buttons drive the loop.

**Test:** operator clicks Send in the console → the card appears at the bottom of the phone thread within
2 seconds → tapping a button shows the reply under that card and disables its buttons; the console
reflects the reply. Earlier messages stay visible.
**Document:** screenshot of each card; short screen recording (backup for the demo video).

## Checkpoint 9 — Vault
**Goal:** saved cards with a search box at `/phone/vault`.

**Test:** after the path, vault shows 2 saved items; search "kidney" finds them; search "xyz" finds none.
**Document:** screenshot. ← **MVP complete here.**

## Checkpoint 11 — Automatic sending
**Goal:** after onboarding and after each answer the backend sends the next card itself (blueprint
§7.8), so the doctor never waits for the operator. `AUTO_SEND=on|off` (default on); `card_sent` events
carry `trigger` (`auto` / `manual`); `/send` stays as the manual override. ION stays general until the
first card reply (§7.6). Picker, guard, scoring and explorer rules unchanged; API responses unchanged.

**Test:** from `backend/`, `python -m app.demo_run` with `AUTO_SEND=on` and with `AUTO_SEND=off` →
`DEMO PATH OK` both times; `python -m app.api_check` against a server with `LLM_MODE=off`, once with
`AUTO_SEND=on` and once with `AUTO_SEND=off` → `API PATH OK` both times; `npm run build` succeeds.
By hand: Reset demo → the label card is already on the phone; each answer brings the next card; the
console timeline says "Sent automatically".

## Checkpoint 12 — Demo freeze
**Goal:** nothing new, only reliability.
- [ ] All external data cached; demo works with Wi-Fi off (except live LLM, which falls back to a fixed list)
- [ ] 3 full dry runs, timed; 2-minute video recorded
- [ ] Devpost writeup, architecture slide, roadmap slide

**Test:** a teammate who didn't build the UI runs the whole demo from a fresh clone.