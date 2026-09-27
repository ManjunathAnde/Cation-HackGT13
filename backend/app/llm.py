"""LLM calls (blueprint §8). The LLM may choose among validated candidates; plain code builds the
candidate list, validates the choice, and falls back.

choose_topic (Checkpoint 11e, the picker's switch points): Gemini → Groq, at most 3 seconds per
provider, no cache; core.py falls back when it returns no topic.
suggest_related (DORMANT since Checkpoint 11e: the explorer offer was replaced by switch points; kept
for llm_check): Redis cache → Gemini → Groq → the specialty's fixed fallback, 5 seconds per provider,
2 seconds per Redis call. Every answer, cached or fresh, is validated before use.
Settings come from backend/.env; values already set in the environment win, so a script or
shell can force LLM_MODE=off. Never prints or logs keys, REDIS_URL, or error text.
"""

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import redis
from dotenv import load_dotenv
from redis.backoff import NoBackoff
from redis.retry import Retry

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TIMEOUT_SECONDS = 5
TOPIC_TIMEOUT_SECONDS = 3  # topic choice runs inside /reply, so it waits less (worst case ~6 s)
REASON_MAX_CHARS = 160
GROQ_MAX_TOKENS = 100  # the answer is ~18 tokens; without a cap Groq assumes ~1300 and the free tier (1000/min) refuses
GEMINI_SERVER_DEADLINE_MS = 10_000  # Gemini rejects deadlines under 10 s; our 5 s limit is enforced below
# Each provider call runs here so we can stop waiting after TIMEOUT_SECONDS. A call we stop waiting
# for finishes in the background (bounded by the SDK timeouts) and its result is ignored.
CALLS = ThreadPoolExecutor(max_workers=4)


class BlockedTopic(ValueError):
    """A provider chose a topic the specialty blocks (e.g. weight management): invalid, and logged by core."""

    def __init__(self, topic):
        super().__init__("blocked topic")
        self.topic = topic
DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "groq": "qwen/qwen3.8-27b"}
KEY_NAMES = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
MODEL_NAMES = {"gemini": "GEMINI_MODEL", "groq": "GROQ_MODEL"}
CODE_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")

PROMPT_VERSION = "1"  # bump when build_prompt changes, so old cached answers are not reused
CACHE_PREFIX = "cation:explorer:v1:"
CACHE_TTL_SECONDS = 86_400
REDIS_TIMEOUT_SECONDS = 2
REDIS_CLIENTS = {}  # one reusable client per REDIS_URL (TLS setup is slow)


# ---------- topic choice (Checkpoint 11e) ----------

def choose_topic(specialty, recent_cards, scores, candidates, blocked, prefer_new, tried=None):
    """Ask Gemini, then Groq, for the next topic among `candidates` (no Redis).

    Return (topic, reason, provider, blocked_suggestions). topic is None when LLM_MODE is off, there
    are no candidates, or every provider fails; core.py then falls back. blocked_suggestions lists
    (topic, provider) for answers that named a blocked topic (each also counts as invalid_output).
    """
    tried = [] if tried is None else tried
    blocked_suggestions = []
    if os.getenv("LLM_MODE", "off") != "live" or not candidates:
        return None, None, None, blocked_suggestions

    models = {provider: os.getenv(MODEL_NAMES[provider]) or DEFAULT_MODELS[provider] for provider in DEFAULT_MODELS}
    prompt = build_topic_prompt(specialty, recent_cards, scores, candidates, prefer_new)
    choice, provider = ask_providers(
        prompt, models, lambda text: parse_choice(text, candidates, blocked), tried,
        timeout=TOPIC_TIMEOUT_SECONDS, rejected=blocked_suggestions,
    )
    if provider is None:
        return None, None, None, blocked_suggestions
    topic, reason = choice
    return topic, reason, provider, blocked_suggestions


def build_topic_prompt(specialty, recent_cards, scores, candidates, prefer_new):
    return (
        "You choose the next research topic for a physician's reading list. "
        "Do not give medical advice or clinical guidance; the reason only says why the topic fits their reading.\n"
        f"Specialty: {specialty}\n"
        f"Their last cards (title, topic, their answer): {json.dumps(recent_cards)}\n"
        f"Their topic scores (higher means more interest): {json.dumps(scores)}\n"
        f"Candidate topics: {json.dumps(list(candidates))}\n"
        + ("They just answered yes twice in a row: prefer a new topic related to what they liked.\n"
           if prefer_new else "")
        + "Choose exactly one topic from the candidate list. Reply with only a JSON object: "
        '{"topic": "<one candidate, copied exactly>", "reason": "<one short line, at most 20 words>"}. '
        "No other text."
    )


def parse_choice(text, candidates, blocked):
    """{"topic": <candidate>, "reason": <one line>} after stripping a code fence; else ValueError."""
    if not isinstance(text, str):
        raise ValueError("no text")
    choice = json.loads(CODE_FENCE.sub("", text))
    if not isinstance(choice, dict):
        raise ValueError("not an object")
    topic, reason = choice.get("topic"), choice.get("reason")
    if topic in blocked:
        raise BlockedTopic(topic)
    if topic not in candidates:
        raise ValueError("topic is not a candidate")
    reason = reason.strip() if isinstance(reason, str) else ""
    if not reason or "\n" in reason or len(reason) > REASON_MAX_CHARS:
        raise ValueError("reason must be one short line")
    return topic, reason


# ---------- explorer suggestions (DORMANT since Checkpoint 11e; used only by llm_check) ----------

def suggest_related(specialty, liked_topic, current_topics, candidates, fallback, tried=None):
    """Return (topics, by); `fallback` (the specialty's list) when LLM_MODE is off or every
    provider fails. If `tried` is a list, one {"provider", "result"} entry is appended per source
    attempted: redis → hit, miss, or unreachable; providers → ok, timeout, rate_limited,
    invalid_output, or error."""
    tried = [] if tried is None else tried
    if os.getenv("LLM_MODE", "off") != "live":
        return list(fallback), "fallback"

    models = {provider: os.getenv(MODEL_NAMES[provider]) or DEFAULT_MODELS[provider] for provider in DEFAULT_MODELS}
    key = cache_key(specialty, liked_topic, current_topics, candidates, models)
    cached, lookup = cache_get(key, candidates)
    if lookup:
        tried.append({"provider": "redis", "result": lookup})
    if cached:
        return cached, "redis"

    prompt = build_prompt(specialty, liked_topic, current_topics, candidates)
    topics, provider = ask_providers(prompt, models, lambda text: parse_topics(text, candidates), tried)
    if provider:
        if lookup == "miss":  # only write if Redis just answered; skips a second timeout
            cache_set(key, topics)
        return topics, provider
    return list(fallback), "fallback"  # never cached


def ask_providers(prompt, models, parse, tried, timeout=TIMEOUT_SECONDS, rejected=None):
    """Gemini, then Groq. Return (parse(answer), provider), or (None, None) if both fail.
    `parse` raises ValueError for an invalid answer; a BlockedTopic is also added to `rejected`."""
    for provider, ask in (("gemini", ask_gemini), ("groq", ask_groq)):
        key = os.getenv(KEY_NAMES[provider])
        if not key:
            continue
        try:
            text = CALLS.submit(ask, prompt, key, models[provider], timeout).result(timeout=timeout)
        except Exception as exc:  # any provider failure moves on to the next provider
            tried.append({"provider": provider, "result": failure_type(exc)})
            continue
        try:
            value = parse(text)
        except ValueError as exc:
            tried.append({"provider": provider, "result": "invalid_output"})
            if isinstance(exc, BlockedTopic) and rejected is not None:
                rejected.append((exc.topic, provider))
            continue
        tried.append({"provider": provider, "result": "ok"})
        return value, provider
    return None, None


# ---------- Redis cache ----------

def cache_key(specialty, liked_topic, current_topics, candidates, models):
    parts = {
        "specialty": specialty,
        "liked_topic": liked_topic,
        "current_topics": sorted(current_topics),
        "candidates": sorted(candidates),
        "models": models,
        "prompt_version": PROMPT_VERSION,
    }
    return CACHE_PREFIX + hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def redis_client():
    """The client for the current REDIS_URL, or None if it isn't set."""
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    if url not in REDIS_CLIENTS:
        REDIS_CLIENTS[url] = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=REDIS_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
            retry=Retry(NoBackoff(), 0),  # no retries, so one call stays within the timeout
        )
    return REDIS_CLIENTS[url]


def cache_get(key, candidates):
    """Return (topics or None, lookup), where lookup is hit, miss, unreachable, or None when
    REDIS_URL isn't set. Cached topics are re-validated against today's candidates."""
    client = redis_client()
    if client is None:
        return None, None
    try:
        value = client.get(key)
    except Exception:  # unreachable or erroring Redis is skipped
        return None, "unreachable"
    try:
        return parse_topics(value, candidates), "hit"
    except ValueError:  # nothing cached, or no longer valid for today's candidates
        return None, "miss"


def cache_set(key, topics):
    client = redis_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(topics), ex=CACHE_TTL_SECONDS)
    except Exception:  # a failed write only means the next call asks the providers again
        pass


def build_prompt(specialty, liked_topic, current_topics, candidates):
    return (
        "You suggest research topics for a physician's reading list. "
        "Do not give medical advice, clinical guidance, or make any decision.\n"
        f"Specialty: {specialty}\n"
        f"The physician wants more on: {json.dumps(liked_topic)}\n"
        f"Topics they already follow: {json.dumps(list(current_topics))}\n"
        f"Candidate topics: {json.dumps(list(candidates))}\n"
        "Choose exactly 2 related topics from the candidate list. "
        "Reply with only a JSON array of 2 strings copied exactly from the candidate list, "
        'for example ["topic one", "topic two"]. No JSON object, no other text.'
    )


def ask_gemini(prompt, key, model, timeout):  # we stop waiting after `timeout`; Gemini's deadline stays 10 s
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=GEMINI_SERVER_DEADLINE_MS))
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return response.text


def ask_groq(prompt, key, model, timeout):
    from groq import Groq

    client = Groq(api_key=key, timeout=timeout, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=GROQ_MAX_TOKENS,
    )
    return response.choices[0].message.content


def parse_topics(text, candidates):
    """A JSON list of 1–2 distinct candidate topics, after stripping a markdown code fence."""
    if not isinstance(text, str):
        raise ValueError("no text")
    topics = json.loads(CODE_FENCE.sub("", text))
    if not isinstance(topics, list) or not 1 <= len(topics) <= 2:
        raise ValueError("not a list of 1-2 items")
    if len(set(topics)) != len(topics) or not all(isinstance(t, str) and t in candidates for t in topics):
        raise ValueError("topics must be distinct candidates")
    return topics


def failure_type(exc):
    """timeout, rate_limited or error, from exception classes and status codes only (never the message)."""
    chain = [e for e in (exc, exc.__cause__, exc.__context__) if e is not None]
    if any("timeout" in type(e).__name__.lower() for e in chain):
        return "timeout"
    if any(type(e).__name__ == "RateLimitError" or 429 in (getattr(e, "status_code", None), getattr(e, "code", None))
           for e in chain):
        return "rate_limited"
    return "error"
