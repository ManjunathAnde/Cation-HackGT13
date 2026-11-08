# ⚡ Cation

*The positively charged intelligence layer for Impiricus ION.*  
Turn every doctor's tap into first-party engagement data while delivering high-signal, compliant medical research they actually want.

---

Medical research publishes faster than clinicians can track—PubMed houses over 40 million biomedical citations, adding 1.6+ million annually. For a Healthcare Professional (HCP), the challenge is surface relevance. Broadcast marketing pushes generic updates that get ignored. 

**Cation replaces broadcast messaging with a real-time, closed-loop feedback engine.** Clinician taps generate immediate first-party signals, tuning topic affinities and updating Impiricus ION's Next Best Action (NBA) while serving curated NIH PubMed research and label-exact brand cards over an RCS-ready feed.

*Deterministic code for compliance and routing. LLMs for semantic topic expansion.*

---

## Why Cation?

Traditional HCP communication relies on vanity metrics (opens, impressions) and broad-specialty blasts. Cation enforces precision:

- **First-party signals over vanity opens:** Every tap directly modifies an auditable affinity score ($+1$ for Yes, $-1$ for Not Interested, $-2$ mutes).
- **Compliance by design:** Clinical and brand lanes are strictly segregated. Brand content enforces verbatim FDA label matches; off-label queries hard-fail to medical affairs.
- **Fail-safe orchestration:** The LLM never touches delivery logic or card queries. It proposes candidate transitions only when triggered by explicit signal streaks, backed by two-tier provider failover and an immutable code fallback.

---

## System Architecture

```text
  DOCTOR · Phone Interface                  IMPIRICUS · Operations Console
  Onboard · Read · Yes/No · Vault           Engagement · Timeline · Next Best Action
        │   ▲                                          ▲
   Taps │   │ Next Card (Auto-Sent)                    │ Live Signals
        ▼   │                                          │
┌─────────────── CATION INTELLIGENCE LAYER · FastAPI ───────────────┐
│                                                                   │
│   Topic Scores ──► Card Picker ──► Compliance Guard ──► Delivery  │
│   (±1 / -0.2)       │              (FDA Verbatim Match,           │
│      ▲              │               Off-Label Guard)              │
│      │              ▼                                             │
│   Reply Events   AI Semantic Expansion at Switch Points           │
│                  Gemini Flash ──► Groq Fallback ──► Rule Fallback │
│                  (Constrained to Code-Validated Topic Candidates) │
│                                                                   │
└──────────┬─────────────────────────────────────────┬──────────────┘
           │ Reads                                   │ Exposes
           ▼                                         ▼
   CURATED RESEARCH LIBRARY                  ION INTEGRATION API
   Brand Lane · Clinical Lane                /profile · /events
   • NIH PubMed (MeSH, RCTs, Reviews)        First-Party Affinity Signals
   • DailyMed / FDA Structured Labels        Per-Doctor Event Stream
