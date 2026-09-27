"""Checkpoint 11c: Dr. Evan (dermatology) end to end, in-process, with the LLM off and auto-send on.

Run from backend/:  python -m app.derm_check
Onboards dr_evan, answers Yes to atopic dermatitis cards (Not interested to others) until the explorer
offers a topic, accepts it, answers a few more cards, then checks the API's specialty validation and
that Dr. Patel's §12 path still passes.
"""

import os
import sys

# Fixed path: set before importing core so .env can't override it.
os.environ["LLM_MODE"] = "off"
os.environ["AUTO_SEND"] = "on"

from fastapi.testclient import TestClient  # noqa: E402

from app import core, demo_run  # noqa: E402
from app import main as api  # noqa: E402

DOCTOR = "dr_evan"
DERMATOLOGY = core.SPECIALTIES["dermatology"]
DERM_TOPICS = set(core.topic_values(DERMATOLOGY))
OZEMPIC_TOPICS = set(core.topic_values(core.SPECIALTIES["endocrinology"]))
MAX_ANSWERS_BEFORE_OFFER = 10
ANSWERS_AFTER_OFFER = 3


def waiting_card():
    active = core.inbox(DOCTOR)["active"]
    assert active is not None and active["type"] == "card", f"expected a waiting card, got {active}"
    return active["card"]


def answer(card, reply):
    result = core.reply(DOCTOR, card["id"], reply)
    print(f"   {card['id']:12s} {card['topics'][0]:26s} → {reply:15s} scores {core.profile(DOCTOR)['topics']}")
    return result


def run_evan():
    profile = core.onboard(
        doctor_id=DOCTOR,
        name="Dr. Evan",
        specialty=" Dermatology ",
        conditions=["plaque psoriasis", "atopic dermatitis"],
        interests=["hidradenitis suppurativa"],
        frequency="weekly",
    )
    print(f"== Onboard Dr. Evan\n   specialty stored as sent: {profile['specialty']!r}\n   scores: {profile['topics']}")
    assert profile["topics"] == {"psoriasis": 1, "atopic dermatitis": 1, "hidradenitis suppurativa": 1}
    assert profile["specialty"] == " Dermatology "

    print("\n== Answers until the explorer offers a topic")
    offer = None
    for _ in range(MAX_ANSWERS_BEFORE_OFFER):
        card = waiting_card()
        offer = answer(card, "yes" if "atopic dermatitis" in card["topics"] else "not_interested")["offer"]
        if offer:
            break
    assert offer, "no offer after the atopic dermatitis answers"
    print(f"   offer: {offer}")
    assert core.inbox(DOCTOR)["active"]["type"] == "offer", "no card may be sent while the offer is pending"

    core.topic_reply(DOCTOR, offer, "yes")
    print(f"\n== Accepted {offer}; {ANSWERS_AFTER_OFFER} more answers")
    for _ in range(ANSWERS_AFTER_OFFER):
        answer(waiting_card(), "yes")
    return offer


def show_timeline():
    print("\n== Dr. Evan's events")
    for event in core.doctor_events(DOCTOR):
        details = {k: v for k, v in event.items() if k not in ("t", "doctor", "type", "scores", "title")}
        print(f"   {event['type']:14s} {details}")


def check_evan(offer):
    events = core.doctor_events(DOCTOR)
    sent = [core.CARDS_BY_ID[event["card"]] for event in events if event["type"] == "card_sent"]
    print(f"\n== Cards sent to Dr. Evan: {[card['id'] for card in sent]}")
    assert len(sent) >= 5
    for card in sent:
        assert card["kind"] == "study" and card["lane"] == "clinical", card["id"]
        assert set(card["topics"]) <= DERM_TOPICS and not set(card["topics"]) & OZEMPIC_TOPICS, card["id"]
    offered = [event for event in events if event["type"] == "topic_offered"]
    assert [event["topic"] for event in offered] == [offer]
    assert offer in DERMATOLOGY["explorer_candidates"] and offered[0]["by"] == "fallback"
    assert not [event for event in events if event["type"] in ("topic_blocked", "card_blocked")], \
        "no blocks for dermatology (no weight management, no label card)"


def check_api():
    client = TestClient(api.app)
    evan = {"id": DOCTOR, "name": "Dr. Evan", "specialty": "dermatology", "conditions": ["plaque psoriasis"],
            "interests": [], "frequency": "weekly"}
    cases = [
        ("unsupported specialty", {**evan, "specialty": "cardiology"}, "Unsupported specialty: cardiology"),
        ("dermatology + Ozempic interest", {**evan, "interests": ["ozempic safety"]},
         "Interest is not an approved topic: ozempic safety"),
        ("dermatology + endocrinology condition", {**evan, "conditions": ["type 2 diabetes"]},
         "Unknown condition: type 2 diabetes"),
    ]
    print("\n== API validation")
    for name, body, detail in cases:
        response = client.post("/onboard", json=body)
        print(f"   {name}: {response.status_code} {response.json()}")
        assert (response.status_code, response.json()) == (422, {"detail": detail})
    response = client.get("/specialties")
    body = response.json()
    print(f"   GET /specialties: {response.status_code} "
          f"{[(s['value'], [c['label'] for c in s['conditions']]) for s in body]}")
    assert response.status_code == 200 and [s["value"] for s in body] == ["endocrinology", "dermatology"]
    assert set(body[1]) == {"value", "label", "conditions", "topics"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    offer = run_evan()
    show_timeline()
    check_evan(offer)
    check_api()
    print("\n== Dr. Patel's §12 path afterwards")
    demo_run.main()
    print("\nDERM CHECK OK")


if __name__ == "__main__":
    main()
