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
2. Sends research cards over RCS with two buttons: "Yes, more on this" / "Not interested"
3. Updates per-topic scores from every reply
4. Finds new research on topics the doctor likes and proposes related topics
5. Blocks anything not supported by the drug's FDA label
6. Exposes the learned profile and reply log for ION to use

**Principle.** Plain code makes every decision. The LLM only suggests, and every LLM output
is validated before use.

---

## 2. Scope

**In scope (MVP):** one doctor (Dr. Patel), one drug (Ozempic), onboarding, RCS mockup,
intelligence loop, vault, metrics page, simulated ION panel.

**Out of scope:** real ION integration, real patient data, authentication, databases,
deployment, additional doctors or drugs, brand-level aggregate view, score chart (needs approval),
persistence of doctor state to disk, billing, inventory.

**Separate track (teammate-owned):** real RCS delivery via Google RCS for Business test mode.
It must call the same reply logic as the mockup (see §10).

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
  request (except the explorer's LLM call from Checkpoint 10, which falls back to a fixed answer).

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
- `summary`: one neutral line; for studies, written from the title only.

### 5.3 Event
Every event: `t` (epoch seconds, float), `type`, `doctor`, plus the details below.

| type | details |
| --- | --- |
| onboarded | topics |
| card_sent | card, title, topic (the topic it was picked for), reason (guard pass reason) |
| card_blocked | card, reason |
| reply | card, answer, scores (after update) |
| topic_muted | topic |
| topic_offered | topic, by |
| topic_blocked | topic, reason, by |
| topic_answer | topic, answer |

`by` is `stub` (Checkpoints 3–9), then `gemini`, `groq`, or `cache` (Checkpoint 10+).

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
- Suggestions: 2 related topics from the candidate list — the fixed stub
  `["cardio-kidney-metabolic care", "weight management"]` until Checkpoint 10, then the LLM.
- Processing suggestions in order: skip topics the doctor has or has muted; topics not approved →
  logged `topic_blocked` with reason `outside Ozempic approved uses → route to medical information`;
  the first remaining approved topic becomes the offer (logged `topic_offered`,
  set as `pending_offer`). Remaining suggestions are still checked for blocking and logging.
- Stop after the first topic that produces an offer. At most one offer per reply.
- If `pending_offer` is already set, do not create a new offer (blocked topics are still logged).
- `/topic-reply` yes → topic added at score 1 and to `added`; either answer clears `pending_offer`.

### 7.6 Mock ION
- No card sent yet → pick `General update for <specialty>`, why `specialty only`.
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

---

## 8. LLM Usage (Checkpoint 10+)

| Use | Output validation |
| --- | --- |
| Explorer related topics | Every topic must be in the candidate list; otherwise use the stub |
| PubMed query wording (optional) | Must return ≥1 result, else use the §6 MeSH query |
| One-line study summary (optional) | Plain text, ≤ 20 words, no clinical advice |

- Order: Gemini → Groq → cache. Timeout 8 s per provider. Log which one answered in `by`.
- Prompts request JSON only.
- Prohibited: clinical guidance, medical advice, generating claims, making any decision.
- Never send real personal or patient data to an LLM.

---

## 9. Data Sources

| Source | Used for | Access |
| --- | --- | --- |
| DailyMed (NIH) | Ozempic label: label card + guard sentences | Copied manually into `label.json` and the label card |
| PubMed E-utilities (NIH) | Study cards by MeSH topic | Offline script → `cache.json` |

PubMed rules: filters `(randomized controlled trial[pt] OR systematic review[pt] OR meta-analysis[pt])
AND humans[MeSH]`, last 2 years; include `tool` and `email` parameters; ≤ 3 requests/second;
store title, journal, date, and link only — never abstracts.

---

## 10. API

All request/response bodies use Pydantic models with examples (visible in Swagger at `/docs`).

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | /health | — | `{ ok: true }` |
| POST | /onboard | id, name, specialty, conditions, interests, frequency | public profile (§5.1) |
| GET | /next-card/{doctor_id} | — | `{ card: Card \| null }` |
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

**RCS webhook (separate track):** maps the sender's phone number to a doctor id and the button
text to an answer ("Yes, more on this" → `yes`, "Not interested" → `not_interested`,
"Yes" → topic `yes`, "No thanks" → topic `no`), then calls the same logic as `/reply` or `/topic-reply`.

---

## 11. Frontend

API base URL from `VITE_API_URL`, default `http://localhost:8000`.

| Page | Shows | Calls |
| --- | --- | --- |
| Onboarding | Form: name, specialty, practice conditions, interests, frequency. Note: "practice-level only, no patient details" | /onboard |
| RCS phone | Phone-shaped card: title, summary, source, "Read source" link, two buttons; expansion offers as Yes / No thanks | /next-card, /reply, /topic-reply |
| Vault | Saved cards with a search box | /vault |
| Metrics | Timeline, topic scores, engagement score, reply rate, yes rate, topics added, saved | /metrics |
| ION panel | Current pick and why (labeled "simulated") | /profile |

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

---

## 13. Allowed Dependencies

- Backend: fastapi, uvicorn[standard], pydantic, python-dotenv, httpx, google-genai, groq
- Frontend: react, react-dom, vite, @vitejs/plugin-react

Anything else requires approval. Tests use plain `assert` scripts (no pytest).

---

## 14. Open Items

- [ ] Verbatim Ozempic kidney-indication sentence from DailyMed (Checkpoint 4)
- [ ] Real PubMed studies for the demo path (Checkpoint 4)
- [ ] Gemini and Groq model names confirmed against current provider lists (Checkpoint 10)