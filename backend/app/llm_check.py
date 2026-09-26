"""Checkpoint 10a: check the explorer's LLM failover Gemini → Groq → fallback, live.

Run from backend/:  python -m app.llm_check
Keys are hidden in memory only (os.environ); backend/.env is never edited.
"""

import os
import sys

from app import core, llm

# Dr. Patel's context after step 3 of blueprint §12.
SPECIALTY = "endocrinology"
LIKED_TOPIC = "kidney outcomes"
CURRENT_TOPICS = ["glycemic control", "kidney outcomes", "ozempic safety"]


def run_case(title, hidden_keys):
    for name in hidden_keys:
        os.environ.pop(name, None)
    tried = []
    topics, by = llm.suggest_related(SPECIALTY, LIKED_TOPIC, CURRENT_TOPICS, core.CANDIDATE_TOPICS, tried=tried)
    print(f"\n== {title}")
    print(f"   by:              {by}")
    print(f"   suggestions:     {topics}")
    print(f"   providers_tried: {tried}")
    assert 1 <= len(topics) <= 2 and all(topic in core.CANDIDATE_TOPICS for topic in topics)
    return by


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ["LLM_MODE"] = "live"
    print(f"models: gemini={os.getenv('GEMINI_MODEL') or llm.DEFAULT_MODELS['gemini']}, "
          f"groq={os.getenv('GROQ_MODEL') or llm.DEFAULT_MODELS['groq']}")

    results = [
        run_case("Both keys present", []),
        run_case("Gemini key hidden (in memory)", ["GEMINI_API_KEY"]),
        run_case("Both keys hidden (in memory)", ["GROQ_API_KEY"]),
    ]
    assert results == ["gemini", "groq", "fallback"], results
    print("\nLLM CHECK OK")


if __name__ == "__main__":
    main()
