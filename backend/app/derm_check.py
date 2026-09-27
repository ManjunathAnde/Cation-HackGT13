"""Checkpoints 11c and 11e: Dr. Evan (dermatology) end to end, in-process, with the LLM off and auto-send on.

Run from backend/:  python -m app.derm_check
Onboards dr_evan, answers Yes to 10 cards (the §12 Dr. Evan path: topic runs, switch points, related
cards), checks that only dermatology research appears, then the API's specialty validation and that
Dr. Patel's §12 path still passes.
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
NEW_RELATED = "A new topic related to what you liked."
TOP_TOPIC = "One of your top-scoring topics."
NEXT_HIGHEST = "Your next highest-scoring topic."
# §12 Dr. Evan (Checkpoint 11e): Yes to every card. (card, topic, related topics or None)
PATH = [
    ("pm-39018058", "atopic dermatitis", None),
    ("pm-37678572", "atopic dermatitis", None),
    ("pm-38499325", "psoriatic arthritis", ["atopic dermatitis"]),
    ("pm-33789011", "psoriatic arthritis", ["atopic dermatitis"]),
    ("pm-36191689", "atopic dermatitis", ["psoriatic arthritis"]),
    ("pm-27518661", "hidradenitis suppurativa", None),
    ("pm-36746171", "hidradenitis suppurativa", None),
    ("pm-31583255", "psoriasis", ["hidradenitis suppurativa"]),
    ("pm-37121476", "psoriasis", ["hidradenitis suppurativa"]),
    ("pm-38795716", "hidradenitis suppurativa", ["psoriasis"]),
]
SWITCHES = [
    ("psoriatic arthritis", "yes_streak", NEW_RELATED),
    ("atopic dermatitis", "yes_streak", TOP_TOPIC),
    ("hidradenitis suppurativa", "topic_exhausted", NEXT_HIGHEST),
    ("psoriasis", "yes_streak", TOP_TOPIC),
    ("hidradenitis suppurativa", "yes_streak", TOP_TOPIC),
    ("psoriasis", "topic_exhausted", NEXT_HIGHEST),
]
WAITING_AT_END = "pm-39469713"


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

    print(f"\n== Yes to {len(PATH)} cards")
    for number, (card_id, _, related_topics) in enumerate(PATH, 1):
        message = core.inbox(DOCTOR)["active"]
        assert message is not None and message["type"] == "card", f"expected a waiting card, got {message}"
        card = message["card"]
        result = core.reply(DOCTOR, card["id"], "yes")
        related = f"  related to {message['related']['topics']}" if message["related"] else ""
        print(f"   {number:2d}. {card['id']:12s} {card['topics'][0]:26s} → yes  scores {core.profile(DOCTOR)['topics']}{related}")
        assert card["id"] == card_id, (number, card["id"], card_id)
        assert (message["related"] or {}).get("topics") == related_topics, (number, message["related"])
        assert result["offer"] is None


def show_timeline():
    print("\n== Dr. Evan's events")
    for event in core.doctor_events(DOCTOR):
        details = {k: v for k, v in event.items() if k not in ("t", "doctor", "type", "scores", "title")}
        print(f"   {event['type']:14s} {details}")


def check_evan():
    events = core.doctor_events(DOCTOR)
    sent = [(event["card"], event["topic"]) for event in events if event["type"] == "card_sent"]
    print(f"\n== Cards sent to Dr. Evan: {[card_id for card_id, _ in sent]}")
    assert sent == [(card_id, topic) for card_id, topic, _ in PATH] + [(WAITING_AT_END, "psoriasis")], sent
    for card_id, _ in sent:
        card = core.CARDS_BY_ID[card_id]
        assert card["kind"] == "study" and card["lane"] == "clinical", card_id
        assert set(card["topics"]) <= DERM_TOPICS and not set(card["topics"]) & OZEMPIC_TOPICS, card_id
    chosen = [(e["topic"], e["trigger"], e["reason"]) for e in events if e["type"] == "topic_chosen"]
    assert chosen == SWITCHES, chosen
    assert all(topic in DERM_TOPICS for topic, _, _ in chosen)
    assert not [e for e in events if e["type"] in ("topic_offered", "topic_blocked", "card_blocked")], \
        "no offers or blocks for dermatology (no weight management, no label card)"
    metrics = core.metrics(DOCTOR)
    print(f"   metrics: engagement {metrics['engagement_score']}, yes rate {metrics['yes_rate']}, "
          f"added {metrics['topics_added']}, saved {metrics['saved']}")
    assert (metrics["engagement_score"], metrics["reply_rate"], metrics["yes_rate"]) == (85, 1.0, 1.0)
    assert (metrics["topics_added"], metrics["muted"], metrics["saved"]) == (1, 0, 10)


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
    run_evan()
    show_timeline()
    check_evan()
    check_api()
    print("\n== Dr. Patel's §12 path afterwards")
    demo_run.main()
    print("\nDERM CHECK OK")


if __name__ == "__main__":
    main()
