"""LLM suggestions for the explorer (blueprint §8). The LLM only suggests; core.py decides.

Order: Gemini → Groq → fixed fallback. We wait at most 5 seconds per provider, and its output
is validated before use. Settings come from backend/.env; values already set in the
environment win, so a script or shell can force LLM_MODE=off.
Never prints or logs key values or provider error text.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FALLBACK = ["cardio-kidney-metabolic care", "weight management"]
TIMEOUT_SECONDS = 5
GEMINI_SERVER_DEADLINE_MS = 10_000  # Gemini rejects deadlines under 10 s; our 5 s limit is enforced below
# Each provider call runs here so we can stop waiting after TIMEOUT_SECONDS. A call we stop waiting
# for finishes in the background (bounded by the SDK timeouts) and its result is ignored.
CALLS = ThreadPoolExecutor(max_workers=4)
DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "groq": "qwen/qwen3.8-27b"}
KEY_NAMES = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
MODEL_NAMES = {"gemini": "GEMINI_MODEL", "groq": "GROQ_MODEL"}
CODE_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")


def suggest_related(specialty, liked_topic, current_topics, candidates, tried=None):
    """Return (topics, by). If `tried` is a list, one {"provider", "result"} entry is
    appended per provider attempted; result is ok, timeout, invalid_output, or error."""
    tried = [] if tried is None else tried
    if os.getenv("LLM_MODE", "off") != "live":
        return list(FALLBACK), "fallback"

    prompt = build_prompt(specialty, liked_topic, current_topics, candidates)
    for provider, ask in (("gemini", ask_gemini), ("groq", ask_groq)):
        key = os.getenv(KEY_NAMES[provider])
        if not key:
            continue
        model = os.getenv(MODEL_NAMES[provider]) or DEFAULT_MODELS[provider]
        try:
            text = CALLS.submit(ask, prompt, key, model).result(timeout=TIMEOUT_SECONDS)
        except Exception as exc:  # any provider failure moves on to the next provider
            tried.append({"provider": provider, "result": failure_type(exc)})
            continue
        try:
            topics = parse_topics(text, candidates)
        except ValueError:
            tried.append({"provider": provider, "result": "invalid_output"})
            continue
        tried.append({"provider": provider, "result": "ok"})
        return topics, provider
    return list(FALLBACK), "fallback"


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


def ask_gemini(prompt, key, model):
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


def ask_groq(prompt, key, model):
    from groq import Groq

    client = Groq(api_key=key, timeout=TIMEOUT_SECONDS, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
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
    """timeout or error, from the exception class names only (never the message)."""
    chain = [exc, exc.__cause__, exc.__context__]
    if any(e is not None and "timeout" in type(e).__name__.lower() for e in chain):
        return "timeout"
    return "error"
