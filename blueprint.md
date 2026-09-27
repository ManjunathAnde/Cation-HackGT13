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
4. Sends research in short topic runs and, at each switch point, picks the next topic (related topics
   after two Yes answers in a row)
5. Blocks anything not supported by the drug's FDA label
6. Exposes the learned profile and reply log for ION to use

**Principle.** The LLM may choose among validated candidates; plain code builds the candidate list,
validates the choice, and falls back. Everything else (scoring, muting, the guard, blocking, sending) is
decided by plain code, and every LLM output is validated before use.

---

## 2. Scope

**In scope (MVP):** one doctor (Dr. Patel), one drug (Ozempic), onboarding, phone page,
intelligence loop, vault, metrics page, simulated ION panel.

**Added in Checkpoint 11c:** a second specialty, dermatology (demo doctor Dr. Evan), configured in
`backend/data/specialties.json` (§6). Dermatology has no drug and no label: clinical-lane research only.

**Out of scope:** real ION integration, real patient data, authentication, databases,
deployment, additional drugs or specialties beyond §6, brand-level aggregate view, score chart (needs approval),
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
       files: data/label.json, data/cache.json, data/specialties.json · LLM: Gemini → Groq → cache
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
| specialty | string | e.g. `endocrinology`; must be a configured specialty (§6), matched trimmed and case-insensitive, stored as sent |
| conditions | string[] | practice-level only; must be conditions of the doctor's specialty (§6) |
| interests | string[] | must be topics of the doctor's specialty (§6) |
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
  "topics": [], "claims": [], "kind": "label | study", "year": 0, "lane": "brand | clinical" }
```
- `claims`: clinical sentences; must match the label (§7.4). Studies always have `claims: []`.
- Studies have exactly one topic: the topic assigned when the study was chosen (§9).
- `summary`: one neutral line; for studies, `<journal>, <publication date>`.
- `year` (integer): publication year; for the label card, the label's effective year.
- `lane`: `brand` (the drug or its class, §9) or `clinical` (treatment evidence for the doctor's
  conditions, §9). `year` and `lane` are stored in `cache.json` only; the API's Card model ignores them,
  so responses keep the eight fields above.

### 5.3 Event
Every event: `t` (epoch seconds, float), `type`, `doctor`, plus the details below.

| type | details |
| --- | --- |
| onboarded | topics |
| card_sent | card, title, topic (the topic it was picked for), reason (guard pass reason), trigger (`auto` or `manual`, §7.8), related (`{topics, reason}`, only for cards in a run started by a Yes-streak switch, §7.3) |
| card_blocked | card, reason |
| reply | card, answer, scores (after update) |
| topic_muted | topic |
| topic_offered | topic, by, providers_tried (no longer produced since 11e) |
| topic_blocked | topic, reason, by, providers_tried |
| topic_answer | topic, answer (no longer produced since 11e: nothing creates offers) |
| topic_chosen | topic, reason, by, providers_tried, trigger (`run_limit`, `yes_streak` or `topic_exhausted`, §7.3) |

`by` is `stub` before Checkpoint 10a, then `redis`, `gemini`, `groq`, or `fallback` (10b adds `redis`).
`providers_tried` lists each source attempted with its result, Redis first, e.g.
`[{"provider": "redis", "result": "miss"}, {"provider": "gemini", "result": "timeout"}, {"provider": "groq", "result": "ok"}]`.
Redis result ∈ `hit`, `miss`, `unreachable` (no Redis entry when `REDIS_URL` is not set); provider
result ∈ `ok`, `timeout`, `rate_limited` (HTTP 429), `invalid_output`, `error` (never error text, keys, or `REDIS_URL`).
Empty when `LLM_MODE=off`.

### 5.4 Files
- `backend/data/label.json`: `drug`, `approved_topics[]`, `sentences[]` (verbatim label text)
- `backend/data/cache.json`: `cards[]` in the card format, in the order the picker uses
- `backend/data/specialties.json`: `specialties[]`, each with `value`, `label`, `conditions[]`
  (`value`, `label`, `topic`), `topics[]` (`value`, `label`), `explorer_candidates[]`, `blocked`
  (topic → reason), `brand` (drug or null), `label_cards` (bool), `fallback[]`. Checked at startup (§6).

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

Topics are configured per specialty in `backend/data/specialties.json` and loaded at startup; logic reads
the doctor's specialty config, never hard-coded lists. The server refuses to start if the file is
inconsistent: every condition maps to one of the specialty's topics; explorer candidates are exactly the
topics followed by the blocked topics; the fallback is within the candidates; and a specialty with label
cards has exactly `label.json`'s `approved_topics`, in order.

| Setting | endocrinology (Dr. Patel) | dermatology (Dr. Evan) |
| --- | --- | --- |
| Conditions → topic | `type 2 diabetes` → glycemic control ("Type 2 diabetes (T2D)"); `chronic kidney disease` → kidney outcomes ("Chronic kidney disease (CKD)") | `plaque psoriasis` → psoriasis ("Plaque psoriasis"); `atopic dermatitis` → atopic dermatitis ("Atopic dermatitis (eczema)"); `hidradenitis suppurativa` → hidradenitis suppurativa ("Hidradenitis suppurativa (HS)") |
| Topics | the Ozempic approved topics below | psoriasis, atopic dermatitis, hidradenitis suppurativa, psoriatic arthritis |
| Explorer candidates | topics + `weight management` | topics |
| Blocked | `weight management` → `outside Ozempic approved uses → route to medical information` | none |
| Brand / label cards | ozempic / yes | none / no (never receives label cards) |
| Fallback suggestions | `["cardio-kidney-metabolic care", "weight management"]` | `["psoriatic arthritis", "psoriasis"]` |

Each condition and topic also has a display label (`GET /specialties`, §10).

**Approved topics (Ozempic, endocrinology):**
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

**Dr. Evan (dermatology) topic → MeSH query map** (study cards only; these topics are not Ozempic
approved topics, cannot be onboarded yet, and are never picked for Dr. Patel):
- psoriasis → `"Psoriasis"[MeSH]`
- atopic dermatitis → `"Dermatitis, Atopic"[MeSH]`
- hidradenitis suppurativa → `"Hidradenitis Suppurativa"[MeSH]`
- psoriatic arthritis → `"Arthritis, Psoriatic"[MeSH]`

---

## 7. Intelligence Rules

### 7.1 Onboarding
The specialty must be configured (§6; trimmed, case-insensitive), else `Unsupported specialty: <value>`
(API: 422). Conditions map to topics via that specialty's map; interests are used as-is. Every starting
topic = 1. A condition or interest outside that specialty → rejected (API: 422, same messages as before).

### 7.2 Scorer
- Reply `yes` → +1, `not_interested` → −1, `no_reply` → −0.25
- Applied to each card topic **the doctor already has**; other card topics are ignored.
- Score ≤ −2 → topic muted (logged `topic_muted` once). Muted topics keep updating their score
  but stay muted. No unmuting in MVP.
- `yes` → card id added to the vault (no duplicates).

### 7.3 Picker (Checkpoint 11e: topic runs and switch points)
Candidates exclude cards already sent or blocked. The same picker serves `/send` and auto-send (§7.8);
runs and streaks are computed from the doctor's history, so both modes behave the same.
1. **Label cards first** (only for specialties with `label_cards: true`; others never receive label cards):
   a label card qualifies if any of its topics is an unmuted doctor topic.
   Multiple label cards → cache file order. A label card is "picked for" its **first** topic and counts
   toward that topic's run.
2. **First card** (nothing sent yet, no label card): rank unmuted doctor topics by score (highest first);
   ties: never picked first, then smallest `last_picked`, then alphabetical. No AI call.
3. **Topic runs:** at most **2** cards in a row from the same topic, never 3. Within a run, the next card
   comes from the same topic, no AI call.
4. **Switch points** (the next topic is chosen, logged as `topic_chosen`), checked in this order:
   - `yes_streak`: the doctor has just answered Yes twice in a row (a `not_interested` or `no_reply`
     resets the streak; every switch resets it);
   - `run_limit`: the current topic has just been sent twice in a row;
   - `topic_exhausted`: within a run, the current topic has no card left that passes the guard, or it
     was muted.
5. **Choosing the topic** (§8): candidates = the doctor's unmuted topics plus her specialty's other
   topics, keeping only topics with unsent cards and not blocked, and never the current topic when it
   has just had 2 in a row. The AI chooses one (a Yes streak asks it to prefer a new related topic);
   plain code validates it. Fallback (LLM off or every provider failed): highest score (topics not held
   count as 0), then least recently picked, then alphabetical, other than the current topic; after a
   Yes streak, topics the doctor doesn't hold first. Fallback reasons: `Your next highest-scoring topic.`
   (run_limit, topic_exhausted), `A new topic related to what you liked.` (Yes streak, new topic),
   `One of your top-scoring topics.` (Yes streak, topic already held).
6. **After a switch:** a chosen topic the doctor doesn't hold is added at score 1 (and to `added`, so it
   counts as a topic added). The next card comes from it; if it has no card that passes the guard, the
   next topic in fallback order is tried; if none has one, nothing is sent. Cards in a run started by a
   Yes-streak switch carry `related: {topics: <the liked topics>, reason}` (on `card_sent` and the inbox
   card message).
7. Within a topic, cards in cache file order. Each candidate goes through the guard. Blocked → logged,
   added to `blocked`, and the picker continues in the same call.
8. On send: card id appended to `sent`; `last_picked[picked-for topic]` = length of `sent`;
   `last_card_id` = card id.
9. Nothing left → no card (`null`).

### 7.4 Guard
- Every sentence in `claims` must exactly equal a sentence in `label.json` (for a specialty without
  label cards there is no label, so any claim is blocked), after trimming
  leading/trailing whitespace. Otherwise block with reason `Unsupported claim: <sentence>`.
- Cards with no claims pass with reason `Title + link only`; label cards that pass use
  `Claims match label`.

### 7.5 Explorer (replaced in Checkpoint 11e)
Since Checkpoint 11e the Yes-streak switch point (§7.3) replaces the explorer offer: nothing creates offers,
`/reply` always returns `offer: null`, and `/topic-reply`, the inbox offer message and the Brief's offer card
remain only for compatibility (`/topic-reply` answers 400 `Topic <topic> is not on offer`). The rules below
describe the dormant explorer (`llm.suggest_related`, still exercised by `llm_check`):
- After a reply, check the replied card's topics in their card order. A topic is checked if its score
  is **≥ 3** and it is not in `explored`.
- Each checked topic is added to `explored` (its one chance is used, even if nothing is offered).
- Suggestions: 2 related topics from the specialty's explorer candidates, from the LLM (§8); the
  specialty's fixed fallback (§6) when `LLM_MODE=off` or all providers fail.
- Processing suggestions in order: skip topics the doctor has or has muted; topics outside the
  specialty's topics (its blocked topics) → logged `topic_blocked` with that topic's configured reason
  (endocrinology: `outside Ozempic approved uses → route to medical information`);
  the first remaining specialty topic becomes the offer (logged `topic_offered`,
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
  - `/reply`: after scoring → next card (no offers exist since 11e, so a card always follows).
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
| Next topic at a switch point (§7.3, 11e) | JSON object `{"topic", "reason"}` (code fences stripped): `topic` must be one of the candidates (so never a third card in a row); a blocked topic → logged `topic_blocked` with the specialty's reason and treated as invalid; `reason` one non-empty line, ≤ 160 characters, no medical advice; invalid → next provider, then the plain-code fallback |
| Explorer related topics (dormant since 11e) | Parsed JSON list of 1–2 distinct topics, each in the candidate list (markdown code fences stripped first); otherwise try the next provider, then the fallback |
| PubMed query wording (optional) | Must return ≥1 result, else use the §6 MeSH query |
| One-line study summary (optional) | Plain text, ≤ 20 words, no clinical advice |

- Topic choice (11e): Gemini → Groq → plain-code fallback, **3 s** per provider (worst case about 6 s),
  no Redis. Input: specialty, last 4 answered cards (title, topic, answer), current scores, candidates,
  and after a Yes streak a note to prefer a new related topic. Logged as `topic_chosen` with `by`.
- Explorer (dormant): Redis cache → Gemini → Groq → fallback. Timeout 5 s per provider. Log which one answered in `by`.
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

PubMed rules (`python -m app.fetch_studies`, print-only): every search adds
`(randomized controlled trial[pt] OR systematic review[pt] OR meta-analysis[pt]) AND humans[MeSH]`,
no date limit, sorted by relevance, up to 8 results each; include `tool` and `email` parameters;
≤ 3 requests/second; esearch + esummary only; store title, journal, date, and link only — never abstracts.
- Dr. Patel, brand lane: `(<§6 MeSH query>) AND semaglutide AND (<filters>)`, for every approved topic.
- Dr. Patel, clinical lane: `(<§6 MeSH query>) AND "Diabetes Mellitus, Type 2"[MeSH] AND (<filters>)
  NOT semaglutide`, for every approved topic except `ozempic safety` (brand only).
- Dr. Evan, clinical lane only (no drug term): `<§6 Dr. Evan MeSH query> AND (<filters>)`.
- PMIDs already in `cache.json` are skipped; a PMID found by more than one search is a candidate only
  under its first search.

Selection rule: studies are chosen by a human from the fetch output, then appended to `cache.json`
after the existing cards, in the order chosen (existing cards are never reordered), with the topic
and lane the human assigns.
- **Brand lane:** subcutaneous semaglutide (Ozempic) or GLP-1 receptor agonist class studies in adults
  with type 2 diabetes, including those with heart or kidney disease. Exclude oral semaglutide (a
  different product), studies with another named drug as the focus, type 1 diabetes, and non-diabetic
  obesity populations.
- **Clinical lane:** treatment evidence (trials, systematic reviews, meta-analyses) for the doctor's
  conditions. No claims; title and link only, like every study card.

---

## 10. API

All request/response bodies use Pydantic models with examples (visible in Swagger at `/docs`).

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | /health | — | `{ ok: true }` |
| GET | /specialties | — | `[{ value, label, conditions: [{value, label}], topics: [{value, label}] }]` — the configured specialties (§6), for the entry page |
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
- `/onboard` validation failure (§7.1) → 422, including `Unsupported specialty: <value>`
- `/reply`: `card_id` ≠ `last_card_id`, or already answered → 400
- `/topic-reply`: `topic` ≠ `pending_offer` → 400
- `/send`: doctor has an unanswered card or a pending topic offer → 400

**Automatic sending (§7.8).** With `AUTO_SEND` on (the default), `/onboard`, `/reply` (unless an offer
is now pending) and `/topic-reply` also send the next card before returning; their response bodies
are unchanged. `/send` is the operator's manual override. The `trigger` field appears only in the
event log (`card_sent` in `/events` and the `/metrics` timeline), never in other responses.

**Inbox messages.** `messages` is the doctor's full thread in order, built from the event log
(`card_sent`, `reply`, `topic_offered`, `topic_answer`); blocked cards and blocked topics are not shown.
- Card: `{ "type": "card", "t": <epoch s>, "card": Card, "answer": "yes" | "not_interested" | "no_reply" | null, "related": {topics, reason} | null }`
  (`related` since 11e: set for cards sent in a run started by a Yes-streak switch, §7.3)
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

Checkpoint 11e picker (§7.3). Answers: Yes, Not interested, Yes, Yes, then Yes until 10 cards.

| # | Card | Picked for | Why | Answer | Result |
| --- | --- | --- | --- | --- | --- |
| 0 | Onboard | — | — | — | glycemic control 1, kidney outcomes 1, ozempic safety 1; ION `General update for endocrinology` (also while card 1 waits) |
| 1 | label-ozempic-ckd | kidney outcomes | label first | yes | kidney outcomes 2, ozempic safety 2; saved |
| 2 | pm-41644273 | kidney outcomes | run | not_interested | kidney outcomes 1 |
| — | switch `run_limit` → ozempic safety | | fallback: highest score | | |
| 3 | pm-42594084 | ozempic safety | after switch | yes | ozempic safety 3 |
| 4 | pm-39964295 | ozempic safety | run | yes | ozempic safety 4 |
| — | switch `yes_streak` → cardio-kidney-metabolic care (added) | | new topic first | | |
| 5 | pm-42233552 | cardio-kidney-metabolic care | related to ozempic safety | yes | ckm 2 |
| 6 | pm-39211948 | cardio-kidney-metabolic care | run (related) | yes | ckm 3 |
| — | switch `yes_streak` → cardiovascular outcomes (added) | | | | |
| 7 | pm-27633186 | cardiovascular outcomes | related to ckm | yes | cv 2 |
| 8 | pm-39210781 | cardiovascular outcomes | run (related) | yes | cv 3 |
| — | switch `yes_streak` → ozempic safety (no new topic left) | | | | |
| 9 | pm-38787986 | ozempic safety | related to cv | yes | ozempic safety 5 |
| 10 | pm-40437949 | ozempic safety | run (related) | yes | ozempic safety 6; ION `ozempic safety content` (top score 6) |
| End | switch `yes_streak` → cardio-kidney-metabolic care; `pm-39217553` waiting | | | | engagement 86, reply_rate 1.0, yes_rate 0.9, topics_added 2, muted 0, saved 9 |

Dr. Evan: id `dr_evan`, dermatology; conditions `plaque psoriasis`, `atopic dermatitis`; interests
`hidradenitis suppurativa`; weekly. Answers: Yes to 10 cards. Cards: pm-39018058, pm-37678572 (atopic
dermatitis) → `yes_streak` → psoriatic arthritis (added): pm-38499325, pm-33789011 → `yes_streak` → atopic
dermatitis: pm-36191689 → `topic_exhausted` → hidradenitis suppurativa: pm-27518661, pm-36746171 →
`yes_streak` → psoriasis: pm-31583255, pm-37121476 → `yes_streak` → hidradenitis suppurativa: pm-38795716 →
`topic_exhausted` → psoriasis, pm-39469713 waiting. End: engagement 85, reply_rate 1.0, yes_rate 1.0,
topics_added 1, muted 0, saved 10; only clinical dermatology cards.

The values above hold with `LLM_MODE=off` (every switch uses the plain-code fallback) and are the same
with `AUTO_SEND=on` (cards arrive by themselves) and `AUTO_SEND=off` (the operator sends each with `/send`).
With `LLM_MODE=live` the AI chooses the topic at each switch point and the path may differ. With the LLM
off, weight management is never a candidate, so no `topic_blocked` appears; a live provider that
suggests it is logged as `topic_blocked` (Compliance safeguard) and treated as invalid.

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
- [x] Expanded study set (32 cards; appended after the 7 above, in this order):
      Dr. Patel — glycemic control: 38286487 (brand), 36722623 (brand), 37987208 (clinical);
      cardiovascular outcomes: 27633186 (brand), 39210781 (clinical), 33441402 (clinical);
      kidney outcomes: 38785209 (brand), 31422062 (brand), 33264825 (clinical);
      ozempic safety: 38787986 (brand), 40437949 (brand);
      cardio-kidney-metabolic care: 39211948 (brand), 39217553 (brand), 39608381 (clinical).
      Dr. Evan (all clinical) — psoriasis: 31583255, 37121476, 39469713; atopic dermatitis: 39018058,
      37678572, 36191689; hidradenitis suppurativa: 27518661, 36746171, 38795716;
      psoriatic arthritis: 38499325, 33789011.
- [ ] Gemini and Groq model names confirmed against current provider lists (Checkpoint 10)
- [ ] Run the frontend on the local network so a phone can open /phone: `VITE_API_URL` points to the
      laptop's local IP, both servers listen on the network interface (not only localhost), and CORS
      allows the frontend's local-network origin.