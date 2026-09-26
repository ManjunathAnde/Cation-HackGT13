"""Checkpoint 5: replay Dr. Patel's demo path (blueprint §12) over HTTP.

Needs the backend running on localhost:8000. Run from backend/:  python -m app.api_check
Works with the server's AUTO_SEND on or off: if a card is already waiting after onboarding,
cards arrive automatically; otherwise each card is sent with POST /send.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first and each request waits ~2 s
# before falling back, because uvicorn listens on IPv4 only.
API = "http://127.0.0.1:8000"
DOCTOR = "dr_patel"
GENERAL_ION = {"pick": "General update for endocrinology", "why": "specialty only"}
CARDS = json.loads((Path(__file__).resolve().parent.parent / "data" / "cache.json").read_text(encoding="utf-8"))["cards"]


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


def first_card(kind, topic):
    return next(card for card in CARDS if card["kind"] == kind and topic in card["topics"])


def stop_if_llm_live(timeline):
    """The §12 path is fixed only with the LLM off; a live server makes step 3 vary."""
    explorer = [event for event in timeline if event["type"] in ("topic_offered", "topic_blocked")]
    if any(event["by"] != "fallback" for event in explorer):
        raise SystemExit(
            "Server is running with LLM_MODE=live. Restart it with LLM_MODE=off to run api_check "
            "(the §12 path is fixed only with the LLM off)."
        )


def waiting_card(auto):
    """The card to answer next: already sent automatically, or sent now with POST /send."""
    if auto:
        active = ok("GET", f"/inbox/{DOCTOR}")["active"]
        assert active is not None and active["type"] == "card", f"no card waiting: {active}"
        return active["card"]
    return ok("POST", f"/send/{DOCTOR}")["card"]


def send_and_reply(step, answer, auto):
    card = waiting_card(auto)
    ion_before = ok("GET", f"/profile/{DOCTOR}")["ion"]
    result = ok("POST", "/reply", {"doctor_id": DOCTOR, "card_id": card["id"], "answer": answer})
    profile = ok("GET", f"/profile/{DOCTOR}")
    print(f"\n== Step {step}: {card['id']} → {answer}")
    print(f"   {card['title']}")
    if result["offer"]:
        print(f"   offer:  {result['offer']}")
    print(f"   scores: {profile['topics']}")
    print(f"   ION:    {result['ion']['pick']} ({result['ion']['why']})")
    return card, result, profile, ion_before


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    label_card = first_card("label", "kidney outcomes")
    safety_study = first_card("study", "ozempic safety")
    kidney_study = first_card("study", "kidney outcomes")

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

    card1, _, step1, ion_card1_waiting = send_and_reply(1, "yes", auto)
    twice = call("POST", "/reply", {"doctor_id": DOCTOR, "card_id": card1["id"], "answer": "yes"})
    card2, _, step2, _ = send_and_reply(2, "not_interested", auto)
    card3, reply3, step3, _ = send_and_reply(3, "yes", auto)
    stop_if_llm_live(ok("GET", f"/metrics/{DOCTOR}")["timeline"])

    inbox_before = ok("GET", f"/inbox/{DOCTOR}")
    send_while_pending = call("POST", f"/send/{DOCTOR}")

    topic4 = ok("POST", "/topic-reply", {"doctor_id": DOCTOR, "topic": reply3["offer"], "answer": "yes"})
    step4 = ok("GET", f"/profile/{DOCTOR}")
    print(f"\n== Step 4: accept {reply3['offer']}\n   scores: {step4['topics']}\n   ION:    {topic4['ion']['pick']}")

    metrics = ok("GET", f"/metrics/{DOCTOR}")
    vault = ok("GET", f"/vault/{DOCTOR}?q=kidney")
    inbox = ok("GET", f"/inbox/{DOCTOR}")
    unknown = call("GET", "/profile/nobody")
    print(f"\n== Metrics: engagement {metrics['engagement_score']}, reply rate {metrics['reply_rate']}, "
          f"yes rate {metrics['yes_rate']}, added {metrics['topics_added']}, muted {metrics['muted']}, saved {metrics['saved']}")
    print(f"== Vault ?q=kidney: {[card['id'] for card in vault]}")
    print(f"== Inbox: {[(m['type'], m['card']['id'] if m['type'] == 'card' else m['topic'], m['answer']) for m in inbox['messages']]}")
    print(f"   active: {inbox['active']}")
    print(f"== Errors: reply twice → {twice[0]} {twice[1]['detail']!r}; send while offer pending → "
          f"{send_while_pending[0]} {send_while_pending[1]['detail']!r}; unknown doctor → {unknown[0]} {unknown[1]['detail']!r}")

    # Step 0
    assert step0["topics"] == {"glycemic control": 1, "kidney outcomes": 1, "ozempic safety": 1}
    assert step0["ion"] == GENERAL_ION
    # ION stays general until the first card reply, also while card 1 is waiting
    assert ion_card1_waiting == GENERAL_ION
    # Step 1: label card → yes
    assert card1["id"] == label_card["id"]
    assert step1["topics"] == {"glycemic control": 1, "kidney outcomes": 2, "ozempic safety": 2}
    # Step 2: safety study → not_interested
    assert card2["id"] == safety_study["id"]
    assert step2["topics"]["ozempic safety"] == 1
    # Step 3: kidney study → yes; offer and block
    assert card3["id"] == kidney_study["id"]
    assert step3["topics"]["kidney outcomes"] == 3
    assert reply3["offer"] == "cardio-kidney-metabolic care"
    assert any(
        event["type"] == "topic_blocked" and event["topic"] == "weight management"
        and event["reason"] == "outside Ozempic approved uses → route to medical information"
        and event["by"] == "fallback"
        for event in metrics["timeline"]
    )
    # After the 3rd reply: the offer is active and sending is refused
    active = inbox_before["active"]
    assert active == inbox_before["messages"][-1]
    assert (active["type"], active["topic"], active["answer"]) == ("offer", "cardio-kidney-metabolic care", None)
    assert send_while_pending == (400, {"detail": "Doctor has a pending topic offer"})
    # Step 4: offer accepted
    assert step4["topics"]["cardio-kidney-metabolic care"] == 1
    assert topic4["ion"] == {"pick": "kidney outcomes content", "why": "top score 3 from replies"}
    # End: metrics, vault, inbox
    assert metrics["engagement_score"] == 72 and isinstance(metrics["engagement_score"], int)
    assert metrics["reply_rate"] == 1.0
    assert metrics["yes_rate"] == 0.67
    assert metrics["topics_added"] == 1
    assert metrics["muted"] == 0
    assert metrics["saved"] == 2
    assert [card["id"] for card in vault] == [label_card["id"], kidney_study["id"]]
    answered = [("card", "yes"), ("card", "not_interested"), ("card", "yes"), ("offer", "yes")]
    assert [m["card"]["id"] for m in inbox["messages"][:3]] == [card1["id"], card2["id"], card3["id"]]
    sent = [event for event in metrics["timeline"] if event["type"] == "card_sent"]
    assert [event["trigger"] for event in sent] == [trigger] * len(sent)
    if auto:
        # The offer answer sent the next card, which is now waiting; POST /send was refused while card 1 waited
        kidney_study_2 = [card for card in CARDS if card["kind"] == "study" and "kidney outcomes" in card["topics"]][1]
        assert [(m["type"], m["answer"]) for m in inbox["messages"]] == answered + [("card", None)]
        assert inbox["active"] == inbox["messages"][-1] and inbox["active"]["card"]["id"] == kidney_study_2["id"]
        assert send_while_card_waits == (400, {"detail": "Doctor has an unanswered card"})
    else:
        assert [(m["type"], m["answer"]) for m in inbox["messages"]] == answered
        assert inbox["active"] is None
    # Errors
    assert twice[0] == 400
    assert unknown[0] == 404

    print("\nAPI PATH OK")


if __name__ == "__main__":
    main()
