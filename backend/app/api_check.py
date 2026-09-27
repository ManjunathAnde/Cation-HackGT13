"""Replay Dr. Patel's demo path (blueprint §12, Checkpoint 11e picker) over HTTP.

Needs the backend running on localhost:8000. Run from backend/:  python -m app.api_check
Works with the server's AUTO_SEND on or off: if a card is already waiting after onboarding,
cards arrive automatically; otherwise each card is sent with POST /send.
"""

import json
import sys
import urllib.error
import urllib.request

from app.demo_run import GENERAL_ION, PATH, SWITCHES, WAITING_AT_END

# 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first and each request waits ~2 s
# before falling back, because uvicorn listens on IPv4 only.
API = "http://127.0.0.1:8000"
DOCTOR = "dr_patel"


def call(method, path, body=None):
    """Return (status, json body), including for 4xx responses."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        API + path, data=data, method=method, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())
    except urllib.error.URLError:
        raise SystemExit(f"Backend not reachable at {API}. Start it first.")


def ok(method, path, body=None):
    status, result = call(method, path, body)
    assert status == 200, f"{method} {path} → {status}: {result}"
    return result


def stop_if_llm_live(timeline):
    """The §12 path is fixed only with the LLM off; a live server lets the AI choose the topics."""
    chosen = [event for event in timeline if event["type"] == "topic_chosen"]
    if any(event["by"] != "fallback" for event in chosen):
        raise SystemExit(
            "Server is running with LLM_MODE=live. Restart it with LLM_MODE=off to run api_check "
            "(the §12 path is fixed only with the LLM off)."
        )


def waiting_message(auto):
    """The card message to answer next: already sent automatically, or sent now with POST /send."""
    if not auto:
        ok("POST", f"/send/{DOCTOR}")
    active = ok("GET", f"/inbox/{DOCTOR}")["active"]
    assert active is not None and active["type"] == "card", f"no card waiting: {active}"
    return active


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    step0 = ok("POST", "/onboard", {
        "id": DOCTOR,
        "name": "Dr. Patel",
        "specialty": "endocrinology",
        "conditions": ["type 2 diabetes", "chronic kidney disease"],
        "interests": ["ozempic safety"],
        "frequency": "weekly",
    })
    auto = ok("GET", f"/inbox/{DOCTOR}")["active"] is not None
    trigger = "auto" if auto else "manual"
    print(f"== Server AUTO_SEND: {'on' if auto else 'off'}")
    print(f"== Step 0: onboard\n   scores: {step0['topics']}\n   ION:    {step0['ion']['pick']}")
    send_while_card_waits = call("POST", f"/send/{DOCTOR}") if auto else None

    replies, relateds, cards = [], [], []
    for number, (_, _, answer, _) in enumerate(PATH, 1):
        message = waiting_message(auto)
        ion_before = ok("GET", f"/profile/{DOCTOR}")["ion"]
        result = ok("POST", "/reply", {"doctor_id": DOCTOR, "card_id": message["card"]["id"], "answer": answer})
        if number == 1:
            ion_card1_waiting = ion_before
            twice = call("POST", "/reply", {"doctor_id": DOCTOR, "card_id": message["card"]["id"], "answer": "yes"})
        cards.append(message["card"]["id"])
        relateds.append(message["related"])
        replies.append(result)
        print(f"\n== Step {number}: {message['card']['id']} → {answer}"
              + (f"  (related to {message['related']['topics']})" if message["related"] else ""))
        print(f"   ION:    {result['ion']['pick']} ({result['ion']['why']})")
        if number == 2:
            stop_if_llm_live(ok("GET", f"/metrics/{DOCTOR}")["timeline"])

    metrics = ok("GET", f"/metrics/{DOCTOR}")
    stop_if_llm_live(metrics["timeline"])
    vault = ok("GET", f"/vault/{DOCTOR}?q=kidney")
    inbox = ok("GET", f"/inbox/{DOCTOR}")
    topic_reply = call("POST", "/topic-reply", {"doctor_id": DOCTOR, "topic": "psoriasis", "answer": "yes"})
    unknown = call("GET", "/profile/nobody")
    print(f"\n== Metrics: engagement {metrics['engagement_score']}, reply rate {metrics['reply_rate']}, "
          f"yes rate {metrics['yes_rate']}, added {metrics['topics_added']}, muted {metrics['muted']}, saved {metrics['saved']}")
    print(f"== Switches: {[(e['topic'], e['trigger']) for e in metrics['timeline'] if e['type'] == 'topic_chosen']}")
    print(f"== Vault ?q=kidney: {[card['id'] for card in vault]}")
    print(f"== Inbox active: {inbox['active']['card']['id'] if inbox['active'] else None}")
    print(f"== Errors: reply twice → {twice[0]} {twice[1]['detail']!r}; topic-reply (no offers) → "
          f"{topic_reply[0]} {topic_reply[1]['detail']!r}; unknown doctor → {unknown[0]} {unknown[1]['detail']!r}")

    # Step 0 and the first card
    assert step0["topics"] == {"glycemic control": 1, "kidney outcomes": 1, "ozempic safety": 1}
    assert step0["ion"] == GENERAL_ION
    assert ion_card1_waiting == GENERAL_ION  # ION stays general until the first card reply
    # The path: cards, related lines, no offers
    assert cards == [card_id for card_id, _, _, _ in PATH], cards
    assert [(r or {}).get("topics") for r in relateds] == [topics for _, _, _, topics in PATH], relateds
    assert all(result["offer"] is None for result in replies)
    timeline = metrics["timeline"]
    chosen = [(e["topic"], e["trigger"], e["reason"]) for e in timeline if e["type"] == "topic_chosen"]
    assert chosen == (SWITCHES if auto else SWITCHES[:-1]), chosen
    assert not [e for e in timeline if e["type"] in ("topic_offered", "topic_blocked")]
    sent = [event for event in timeline if event["type"] == "card_sent"]
    assert [event["trigger"] for event in sent] == [trigger] * len(sent)
    # End: metrics, vault, inbox
    assert replies[-1]["ion"] == {"pick": "ozempic safety content", "why": "top score 6 from replies"}
    assert metrics["engagement_score"] == 86 and isinstance(metrics["engagement_score"], int)
    assert metrics["reply_rate"] == 1.0
    assert metrics["yes_rate"] == 0.9
    assert metrics["topics_added"] == 2
    assert metrics["muted"] == 0
    assert metrics["saved"] == 9
    # ?q=kidney matches a title or a topic ("cardio-kidney-metabolic care" counts), in save order
    assert [card["id"] for card in vault] == ["label-ozempic-ckd", "pm-42233552", "pm-39211948", "pm-39210781"]
    assert [m["type"] for m in inbox["messages"]] == ["card"] * (len(PATH) + (1 if auto else 0))
    if auto:
        assert inbox["active"]["card"]["id"] == WAITING_AT_END
        assert send_while_card_waits == (400, {"detail": "Doctor has an unanswered card"})
    else:
        assert inbox["active"] is None
    # Errors
    assert twice[0] == 400
    assert topic_reply == (400, {"detail": "Topic psoriasis is not on offer"})
    assert unknown[0] == 404

    print("\nAPI PATH OK")


if __name__ == "__main__":
    main()
