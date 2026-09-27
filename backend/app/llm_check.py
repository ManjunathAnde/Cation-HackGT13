"""Checkpoints 10a–10b: check the explorer's order Redis → Gemini → Groq → fallback, live.

Run from backend/:  python -m app.llm_check
Keys and REDIS_URL are changed in memory only (os.environ); backend/.env is never edited.
Only this check's own cache key (prefix cation:explorer:v1:) is read or deleted.
"""

import os
import sys

from app import core, llm

# Dr. Patel's context after step 3 of blueprint §12.
SPECIALTY = "endocrinology"
LIKED_TOPIC = "kidney outcomes"
CURRENT_TOPICS = ["glycemic control", "kidney outcomes", "ozempic safety"]
UNREACHABLE_REDIS = "rediss://127.0.0.1:1"
CANDIDATES = core.SPECIALTIES[SPECIALTY]["explorer_candidates"]
FALLBACK = core.SPECIALTIES[SPECIALTY]["fallback"]


def own_key():
    models = {provider: os.getenv(llm.MODEL_NAMES[provider]) or llm.DEFAULT_MODELS[provider]
              for provider in llm.DEFAULT_MODELS}
    key = llm.cache_key(SPECIALTY, LIKED_TOPIC, CURRENT_TOPICS, CANDIDATES, models)
    assert key.startswith(llm.CACHE_PREFIX)
    return key


def delete_own_key():
    llm.redis_client().delete(own_key())


def run_case(title, hidden_keys=(), clear_cache=True):
    if clear_cache:
        delete_own_key()
    for name in hidden_keys:
        os.environ.pop(name, None)
    tried = []
    topics, by = llm.suggest_related(SPECIALTY, LIKED_TOPIC, CURRENT_TOPICS, CANDIDATES, FALLBACK, tried=tried)
    print(f"\n== {title}")
    print(f"   by:              {by}")
    print(f"   suggestions:     {topics}")
    print(f"   providers_tried: {tried}")
    assert 1 <= len(topics) <= 2 and all(topic in CANDIDATES for topic in topics)
    return by, tried


def unreachable_redis_case():
    delete_own_key()
    real_url = os.environ["REDIS_URL"]
    os.environ["REDIS_URL"] = UNREACHABLE_REDIS
    try:
        return run_case("Redis unreachable (REDIS_URL changed in memory)", clear_cache=False)
    finally:
        os.environ["REDIS_URL"] = real_url


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ["LLM_MODE"] = "live"
    print(f"models: gemini={os.getenv('GEMINI_MODEL') or llm.DEFAULT_MODELS['gemini']}, "
          f"groq={os.getenv('GROQ_MODEL') or llm.DEFAULT_MODELS['groq']}")

    cases = [
        run_case("Cache empty, both keys present"),
        run_case("Same call again", clear_cache=False),
        unreachable_redis_case(),
        run_case("Gemini key hidden (in memory)", ["GEMINI_API_KEY"]),
        run_case("Both keys hidden (in memory)", ["GROQ_API_KEY"]),
    ]
    assert [by for by, _ in cases] == ["gemini", "redis", "gemini", "groq", "fallback"], cases
    assert cases[0][1] == [{"provider": "redis", "result": "miss"}, {"provider": "gemini", "result": "ok"}]
    assert cases[1][1] == [{"provider": "redis", "result": "hit"}]
    assert cases[2][1] == [{"provider": "redis", "result": "unreachable"}, {"provider": "gemini", "result": "ok"}]
    assert llm.redis_client().get(own_key()) is None, "the fallback must never be cached"
    print("\nLLM CHECK OK")


if __name__ == "__main__":
    main()
