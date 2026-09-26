# Cation — Blueprint (Source of Truth)

HackGT 13 · Impiricus challenge: "Invent the Next Way We Engage HCPs"
Version 2 · 2026-09-26

---

## 1. Problem and Solution

**Problem.** Pharma messaging to doctors is schedule-driven and generic. When a doctor ignores
a message, the system learns nothing about why. Doctors tune out, and the engagement platform
(Impiricus ION) has no fresh signal about what each doctor actually wants.

**Solution.** Cation is an agent beside ION that:
1. Starts from a doctor's stated profile (specialty, practice conditions, interests)
2. Sends research cards to a phone web page with two buttons: "Yes, more on this" / "Not interested"
3. Updates per-topic scores from every reply
4. Finds new research on topics the doctor likes and proposes related topics
5. Blocks anything not supported by the drug's FDA label
6. Exposes the learned profile and reply log for ION to use

**Principle.** Plain code makes every decision. The LLM only suggests, and every LLM output
is validated before use.

---

## 2. Scope

**In scope (MVP):** one doctor (Dr. Patel), one drug (Ozempic), onboarding, phone page,
intelligence loop, vault, metrics page, simulated ION panel.

**Out of scope:** real ION integration, real patient data, authentication, databases,
deployment, additional doctors or drugs, brand-level aggregate view, score chart (needs approval),
persistence of doctor state to disk, billing, inventory.

Delivery is simulated by a phone web page. The card format stays compatible with RCS rich cards
for future use.

---

## 3. Actors

| Actor | Role in demo |
| --- | --- |
| Doctor | Onboards, receives cards, taps replies, searches vault |
| Impiricus / brand team | Views the metrics page |
| ION (simulated) | Reads `/profile` and `/events`; shows its next pick |

---

## 4. Architecture

```
React (Vite) → FastAPI → core intelligence layer → in-memory doctor state
                               ↑
       files: data/label.json, data/cache.json · LLM: Gemini → Groq → cache
```

- The frontend never makes decisions; it displays API results.
- All decisions live in `backend/app/core.py`.
- Doctor state lives in memory only and resets when the server restarts.
- External APIs are called only by offline scripts that write the cache, never during a demo
  request (except the explorer's LLM call from Checkpoint 10a, which falls back to a fixed list).

---

## 5. Data Model

### 5.1 Doctor profile

**Public fields** (returned by `/onboard` and `/profile`):

| Field | Type | Notes |
| --- | --- | --- |
| id | string | e.g. `dr_patel` |
| name | string | |
| specialty | string | e.g. `endocrinology` |
| conditions | string[] | practice-level only; must be keys of the §6 condition map |
| interests | string[] | must be approved topics (§6) |
| frequency | `daily` \| `weekly` | stored and displayed; not enforced in MVP |
| topics | map topic → number | scores |
| muted | string[] | |
| ion | {pick, why} | computed on each request (§7.6), not stored |

**Internal state** (never returned directly):

| Field | Type | Purpose |
| --- | --- | --- |
| sent | string[] | card ids sent, in order |
| blocked | string[] | card ids the guard blocked; never retried |
| last_card_id | string \| null | the only card that can be answered (§10) |
| answered | string[] | card ids already answered |
| last_picked | map topic → int | sequence number of the last card sent for each topic (§7.3) |
| explored | string[] | topics whose explorer chance is used (§7.5) |
| pending_offer | string \| null | topic currently offered; the only valid `/topic-reply` topic |
| added | string[] | topics added via explorer |
| vault | string[] | saved card ids, no duplicates, in save order |

No age, contact details, or patient information is collected.

### 5.2 Card (fixed format)
```json
{ "id": "", "title": "", "summary": "", "source": "", "link": "",
  "topics": [], "claims": [], "kind": "label | study" }
```
- `claims`: clinical sentences; must match the label (§7.4). Studies always have `claims: []`.
- Studies have exactly one topic: the topic whose MeSH query found them.
- `summary`: one neutral line; for studies, `<journal>, <publication date>`.

### 5.3 Event
Every event: `t` (epoch seconds, float), `type`, `doctor`, plus the details below.

| type | details |
| --- | --- |
| onboarded | topics |
| card_sent | card, title, topic (the topic it was picked for), reason (guard pass reason), trigger (`auto` or `manual`, §7.8) |
| card_blocked | card, reason |
| reply | card, answer, scores (after update) |
| topic_muted | topic |
| topic_offered | topic, by, providers_tried |
| topic_blocked | topic, reason, by, providers_tried |
| topic_answer | topic, answer |

`by` is `stub` before Checkpoint 10a, then `redis`, `gemini`, `groq`, or `fallback` (10b adds `redis`).
`providers_tried` lists each source attempted with its result, Redis first, e.g.
`[{"provider": "redis", "result": "miss"}, {"provider": "gemini", "result": "timeout"}, {"provider": "groq", "result": "ok"}]`.
Redis result ∈ `hit`, `miss`, `unreachable` (no Redis entry when `REDIS_URL` is not set); provider
result ∈ `ok`, `timeout`, `rate_limited` (HTTP 429), `invalid_output`, `error` (never error text, keys, or `REDIS_URL`).
Empty when `LLM_MODE=off`.

### 5.4 Files
- `backend/data/label.json`: `drug`, `approved_topics[]`, `sentences[]` (verbatim label text)
- `backend/data/cache.json`: `cards[]` in the card format, in the order the picker uses

### 5.5 Placeholder data (Checkpoint 3 only; replaced in Checkpoint 4)
Allowed and required for Checkpoint 3. Every placeholder card has title
`PLACEHOLDER: <kind> card for <first topic>`, summary `PLACEHOLDER summary`, and link
`https://pubmed.ncbi.nlm.nih.gov/` for studies or `https://dailymed.nlm.nih.gov/` for the label card.

`cache.json` cards, in this order:
1. `label-ozempic-ckd` — kind `label`,
   topics `["kidney outcomes", "ozempic safety"]`, claims `["PLACEHOLDER: verbatim DailyMed Indications sentence"]`,
   source `DailyMed`
2. `pm-placeholder-safety-1` — kind `study`, topic `ozempic safety`
3. `pm-placeholder-kidney-1` — kind `study`, topic `kidney outcomes`
4. `pm-placeholder-ckm-1` — kind `study`, topic `cardio-kidney-metabolic care`
5. `pm-placeholder-glycemic-1` — kind `study`, topic `glycemic control`

Studies: source `PubMed`, link `https://pubmed.ncbi.nlm.nih.gov/`, claims `[]`.
`label.json` `sentences`: `["PLACEHOLDER: verbatim DailyMed Indications sentence"]`.

---

## 6. Topics

**Approved topics (Ozempic):**
`glycemic control`, `cardiovascular outcomes`, `kidney outcomes`, `ozempic safety`,
`cardio-kidney-metabolic care`

**Candidate topics the explorer may suggest:** the approved list plus `weight management`.
`weight management` is outside Ozempic's approved uses and must always be blocked.

**Condition → topic map:**
- `type 2 diabetes` → `glycemic control`
- `chronic kidney disease` → `kidney outcomes`

**Topic → MeSH query map (Checkpoint 4):**
- glycemic control → `"Glycemic Control"[MeSH]`
- cardiovascular outcomes → `"Cardiovascular Diseases"[MeSH]`
- kidney outcomes → `("Diabetic Nephropathies"[MeSH] OR "Renal Insufficiency, Chronic"[MeSH])`
- ozempic safety → `"Gastrointestinal Diseases"[MeSH]`
- cardio-kidney-metabolic care → `("Cardiovascular Diseases"[MeSH] AND "Kidney Diseases"[MeSH])`

---

## 7. Intelligence Rules

### 7.1 Onboarding
Conditions map to topics via §6; interests are used as-is. Every starting topic = 1.
Unknown condition or non-approved interest → rejected (API: 422).

### 7.2 Scorer
- Reply `yes` → +1, `not_interested` → −1, `no_reply` → −0.25
- Applied to each card topic **the doctor already has**; other card topics are ignored.
- Score ≤ −2 → topic muted (logged `topic_muted` once). Muted topics keep updating their score
  but stay muted. No unmuting in MVP.
- `yes` → card id added to the vault (no duplicates).

### 7.3 Picker
Candidates exclude cards already sent or blocked.
1. **Label cards first:** a label card qualifies if any of its topics is an unmuted doctor topic.
   Multiple label cards → cache file order. A label card is "picked for" its **first** topic.
2. **Otherwise, by topic:** rank unmuted doctor topics by score (highest first). Ties: topics never
   picked rank before picked ones; among picked topics, the one with the smallest `last_picked`
   comes first; remaining ties → alphabetical.
3. Within a topic, cards in cache file order. If the topic has no candidate cards, move to the next topic.
4. Each candidate goes through the guard. Blocked → logged, added to `blocked`, and the picker
   continues in the same call.
5. On send: card id appended to `sent`; `last_picked[picked-for topic]` = length of `sent`;
   `last_card_id` = card id.
6. Nothing left → no card (`null`).

### 7.4 Guard
- Every sentence in `claims` must exactly equal a sentence in `label.json`, after trimming
  leading/trailing whitespace. Otherwise block with reason `Unsupported claim: <sentence>`.
- Cards with no claims pass with reason `Title + link only`; label cards that pass use
  `Claims match label`.

### 7.5 Explorer
- After a reply, check the replied card's topics in their card order. A topic is checked if its score
  is **≥ 3** and it is not in `explored`.
- Each checked topic is added to `explored` (its one chance is used, even if nothing is offered).
- Suggestions: 2 related topics from the candidate list, from the LLM (§8); fixed fallback
  `["cardio-kidney-metabolic care", "weight management"]` when `LLM_MODE=off` or all providers fail.
- Processing suggestions in order: skip topics the doctor has or has muted; topics not approved →
  logged `topic_blocked` with reason `outside Ozempic approved uses → route to medical information`;
  the first remaining approved topic becomes the offer (logged `topic_offered`,
  set as `pending_offer`). Remaining suggestions are still checked for blocking and logging.
- Stop after the first topic that produces an offer. At most one offer per reply.
- If `pending_offer` is already set, do not create a new offer (blocked topics are still logged).
- `/topic-reply` yes → topic added at score 1 and to `added`; either answer clears `pending_offer`.

### 7.6 Mock ION
- No card reply yet (`/reply`; topic-offer answers don't count) → pick `General update for <specialty>`,
  why `specialty only`. This holds while the first card is waiting.
- Otherwise → pick `<top topic> content`, why `top score N from replies`, where top topic is the
  first topic in the §7.3 step 2 ranking and N is formatted without a trailing `.0` (3, 1.75).
- No unmuted topics → pick `No active topics`, why `all topics muted`.

### 7.7 Metrics
- Only card replies (`/reply`) count as replies. Topic-offer answers do not.
- reply_rate = replies other than `no_reply` ÷ replies; yes_rate = `yes` replies ÷ replies.
  Zero replies → both 0.
- engagement_score = reply_rate×40 + yes_rate×40 + min(len(added)×5, 20) − 10×len(muted),
  clipped 0–100, rounded to an integer. Rates are reported rounded to 2 decimals.
  All rounding is half up (72.5 → 73).
- Also: topics_added, muted count, saved count, current scores, full timeline (all events, in order).

### 7.8 Automatic sending (Checkpoint 11)
- Setting `AUTO_SEND` in `backend/.env`: `on` | `off`; unset → `on` (any value other than `off` is on).
- When on, the backend sends the next card itself, synchronously inside the handler, after the
  response has been computed (responses are unchanged):
  - `/onboard`: after the doctor is created → first card.
  - `/reply`: after scoring and the explorer → next card, only if no topic offer is pending.
  - `/topic-reply`: after the answer is recorded → next card.
- Sending uses the same picker and guard as `/send` (§7.3–7.4). Nothing is sent while a card or an
  offer is waiting; if the picker returns no card, nothing is sent (no error).
- `card_sent` events carry `trigger`: `auto` (sent by the handlers above) or `manual` (`/send`),
  in both modes. No other event changes.
- `/send` stays as the operator's manual override with its current rules (400 while a card or offer
  is waiting). With `AUTO_SEND=off`, behavior is as before Checkpoint 11.

---

## 8. LLM Usage (Checkpoint 10a+)

| Use | Output validation |
| --- | --- |
| Explorer related topics | Parsed JSON list of 1–2 distinct topics, each in the candidate list (markdown code fences stripped first); otherwise try the next provider, then the fallback |
| PubMed query wording (optional) | Must return ≥1 result, else use the §6 MeSH query |
| One-line study summary (optional) | Plain text, ≤ 20 words, no clinical advice |

- Order: Redis cache → Gemini → Groq → fallback. Timeout 5 s per provider. Log which one answered in `by`.
- Redis cache (Checkpoint 10b, live mode only; `LLM_MODE=off` skips Redis entirely):
  - Key: `cation:explorer:v1:` + SHA-256 of specialty, liked topic, sorted current topics, sorted
    candidates, both model names, and a prompt version constant.
  - Hit: cached topics are re-validated against the current candidate list (invalid → miss) and
    returned with `by = redis`, with no provider calls.
  - Miss: providers are asked as usual; a valid provider answer is stored with a 24-hour expiry.
    The fallback is never cached.
  - Every Redis call times out after 2 s, with no retries. Unreachable or erroring Redis is skipped
    (`unreachable`) and the providers are tried as usual; no write is attempted after that.
- Settings (backend/.env): `GEMINI_API_KEY`, `GROQ_API_KEY`, `GEMINI_MODEL`, `GROQ_MODEL`,
  `LLM_MODE` (`live` | `off`, default `off`), `REDIS_URL` (Upstash, `rediss://` with TLS).
  A missing key skips that provider; a missing `REDIS_URL` skips the cache.
- Prompts request JSON only.
- Prohibited: clinical guidance, medical advice, generating claims, making any decision.
- Never send real personal or patient data to an LLM.

---

## 9. Data Sources

| Source | Used for | Access |
| --- | --- | --- |
| DailyMed (NIH) | Ozempic label: label card + guard sentences | Copied manually into `label.json` and the label card |
| PubMed E-utilities (NIH) | Study cards by MeSH topic | Offline script → `cache.json` |

PubMed rules: query `(<§6 MeSH query>) AND semaglutide AND (randomized controlled trial[pt] OR
systematic review[pt] OR meta-analysis[pt]) AND humans[MeSH]`, last 2 years; include `tool` and `email`
parameters; ≤ 3 requests/second; store title, journal, date, and link only — never abstracts.

Selection rule: Studies are chosen by a human from the fetch output. Keep only studies about
semaglutide or the GLP-1 receptor agonist class in adults with type 2 diabetes, including those with
cardiovascular or kidney disease. Exclude other drugs, type 1 diabetes, and non-diabetic obesity populations.

---

## 10. API

All request/response bodies use Pydantic models with examples (visible in Swagger at `/docs`).

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | /health | — | `{ ok: true }` |
| POST | /onboard | id, name, specialty, conditions, interests, frequency | public profile (§5.1) |
| POST | /send/{doctor_id} | — | `{ card: Card \| null }` — runs the picker and guard (§7.3–7.4) and sends the next card |
| GET | /inbox/{doctor_id} | — | `{ messages: Message[], active: Message \| null }` — no side effects |
| POST | /reply | `{ doctor_id, card_id, answer }` answer ∈ yes, not_interested, no_reply | `{ offer: string \| null, ion: {pick, why} }` |
| POST | /topic-reply | `{ doctor_id, topic, answer }` answer ∈ yes, no | `{ ion: {pick, why} }` |
| GET | /vault/{doctor_id}?q= | — | Card[] in save order; `q` = case-insensitive substring match on title or any topic |
| GET | /metrics/{doctor_id} | — | metrics from §7.7 |
| GET | /profile/{doctor_id} | — | public profile (§5.1) |
| GET | /events?since= | — | Event[] with `t` > since (epoch seconds) |

Errors:
- Unknown doctor → 404
- `/onboard` validation failure (§7.1) → 422
- `/reply`: `card_id` ≠ `last_card_id`, or already answered → 400
- `/topic-reply`: `topic` ≠ `pending_offer` → 400
- `/send`: doctor has an unanswered card or a pending topic offer → 400

**Automatic sending (§7.8).** With `AUTO_SEND` on (the default), `/onboard`, `/reply` (unless an offer
is now pending) and `/topic-reply` also send the next card before returning; their response bodies
are unchanged. `/send` is the operator's manual override. The `trigger` field appears only in the
event log (`card_sent` in `/events` and the `/metrics` timeline), never in other responses.

**Inbox messages.** `messages` is the doctor's full thread in order, built from the event log
(`card_sent`, `reply`, `topic_offered`, `topic_answer`); blocked cards and blocked topics are not shown.
- Card: `{ "type": "card", "t": <epoch s>, "card": Card, "answer": "yes" | "not_interested" | "no_reply" | null }`
- Offer: `{ "type": "offer", "t": <epoch s>, "topic": string, "answer": "yes" | "no" | null }`

`answer` is `null` until the doctor replies. `active` is the one message that still needs a reply
(the unanswered card or the pending offer), or `null`.

---

## 11. Frontend

API base URL from `VITE_API_URL`, default `http://localhost:8000`.

| Page | Shows | Calls |
| --- | --- | --- |
| Onboarding (`/phone/onboard`) | Form: name, specialty, practice conditions, interests, frequency. Note: "practice-level only, no patient details" | /onboard |
| Brief (`/phone/brief`; `/phone` redirects here) | Phone-shaped, scrollable conversation thread; polls `/inbox` every 2 seconds; newest message at the bottom. Each card shows title, summary, source, and a "Read source" link. Answered items show the doctor's reply; only the active item has buttons ("Yes, more on this" / "Not interested" for cards, Yes / No thanks for offers) | /inbox, /reply, /topic-reply |
| Impiricus console (`/console`; `/` redirects here) | "Send next card" button, plus the metrics and ION panel below | /send |
| Vault (`/phone/vault`) | Saved cards with a search box | /vault |
| Metrics (section of the console) | Timeline, topic scores, engagement score, reply rate, yes rate, topics added, saved | /metrics |
| ION panel (section of the console) | Current pick and why (labeled "simulated") | /profile |

---

## 12. Expected Demo Path (test fixture)

Dr. Patel: id `dr_patel`, endocrinology; conditions `type 2 diabetes`, `chronic kidney disease`;
interests `ozempic safety`; frequency `weekly`.

| Step | Event | Result |
| --- | --- | --- |
| 0 | Onboard | glycemic control 1, kidney outcomes 1, ozempic safety 1; ION: `General update for endocrinology` |
| 1 | Label card (picked for kidney outcomes) → yes | kidney outcomes 2, ozempic safety 2; saved |
| 2 | Safety study (never-picked tie-break) → not_interested | ozempic safety 1 |
| 3 | Kidney study → yes | kidney outcomes 3; saved; offer `cardio-kidney-metabolic care`; `weight management` blocked |
| 4 | Offer → yes | cardio-kidney-metabolic care 1; ION: `kidney outcomes content` (top score 3) |
| End | Metrics | engagement 72, reply_rate 1.0, yes_rate 0.67, topics_added 1, muted 0, saved 2 |

The values above hold with `LLM_MODE=off`. With `LLM_MODE=live` the step-3 offer and block come
from the LLM and may differ.

**Auto path (`AUTO_SEND=on`, §7.8).** Same cards, same order, same values, with no send steps:
onboarding sends the label card; each reply sends the next card, except after step 3 (the offer is
pending); accepting the offer in step 4 sends the next kidney study (`pm-42337824`), which is left
waiting at the end (it does not affect the metrics). ION stays `General update for endocrinology`
until the step-1 reply. With `AUTO_SEND=off`, the operator sends each card with `/send`.

---

## 13. Allowed Dependencies

- Backend: fastapi, uvicorn[standard], pydantic, python-dotenv, httpx, google-genai, groq, redis
- Frontend: react, react-dom, vite, @vitejs/plugin-react

Anything else requires approval. Tests use plain `assert` scripts (no pytest).
The offline fetch scripts use `urllib` from the standard library instead of httpx.

---

## 14. Open Items

- [x] Verbatim Ozempic kidney-indication sentence from DailyMed (Checkpoint 4): label set ID
      `adec4fd2-6858-4c99-91d4-531f5f2a2d79`, version 20, effective 2026-06-01
- [x] Real PubMed studies for the demo path (Checkpoint 4): PMIDs 42594084, 39964295, 41644273,
      42337824, 42233552, 39532398
- [ ] Gemini and Groq model names confirmed against current provider lists (Checkpoint 10)
- [ ] Run the frontend on the local network so a phone can open /phone: `VITE_API_URL` points to the
      laptop's local IP, both servers listen on the network interface (not only localhost), and CORS
      allows the frontend's local-network origin.