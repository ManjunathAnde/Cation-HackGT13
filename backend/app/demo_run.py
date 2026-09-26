"""Checkpoint 3: replay Dr. Patel's demo path (blueprint §12) through core.py, no UI.

Run from backend/:  python -m app.demo_run
"""

import sys

from app import core

DOCTOR = "dr_patel"


def show(title, card=None, answer=None, offer=None):
    profile = core.profile(DOCTOR)
    print(f"\n== {title}")
    if card:
        print(f"   card:   {card['id']}  ({card['title']})")
    if answer:
        print(f"   answer: {answer}")
    if offer:
        print(f"   offer:  {offer}")
    print(f"   scores: {profile['topics']}")
    print(f"   ION:    {profile['ion']['pick']} ({profile['ion']['why']})")
    return profile


def reply_to_next_card(title, answer):
    card = core.next_card(DOCTOR)
    result = core.reply(DOCTOR, card["id"], answer)
    profile = show(title, card=card, answer=answer, offer=result["offer"])
    return card, result, profile


def show_summary(metrics, vault):
    print("\n== Metrics")
    for key in ("engagement_score", "reply_rate", "yes_rate", "topics_added", "muted", "saved", "scores"):
        print(f"   {key}: {metrics[key]}")

    print("\n== Vault")
    for card in vault:
        print(f"   {card['id']}  ({card['title']})")

    print("\n== Timeline")
    start = metrics["timeline"][0]["t"]
    for event in metrics["timeline"]:
        details = {k: v for k, v in event.items() if k not in ("t", "type", "doctor")}
        print(f"   +{event['t'] - start:.3f}s  {event['type']:<14} {details}")


def event_of(timeline, event_type, **match):
    return [
        event for event in timeline
        if event["type"] == event_type and all(event.get(k) == v for k, v in match.items())
    ]


def first_card(kind, topic):
    """The first card in cache order with this kind and topic."""
    return next(card for card in core.CARDS if card["kind"] == kind and topic in card["topics"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    label_card = first_card("label", "kidney outcomes")
    safety_study = first_card("study", "ozempic safety")
    kidney_study = first_card("study", "kidney outcomes")

    core.onboard(
        doctor_id=DOCTOR,
        name="Dr. Patel",
        specialty="endocrinology",
        conditions=["type 2 diabetes", "chronic kidney disease"],
        interests=["ozempic safety"],
        frequency="weekly",
    )
    step0 = show("Step 0: onboard")
    card1, _, step1 = reply_to_next_card("Step 1: card 1", "yes")
    card2, _, step2 = reply_to_next_card("Step 2: card 2", "not_interested")
    card3, reply3, step3 = reply_to_next_card("Step 3: card 3", "yes")
    core.topic_reply(DOCTOR, reply3["offer"], "yes")
    step4 = show("Step 4: accept offer")

    metrics = core.metrics(DOCTOR)
    vault = core.vault(DOCTOR)
    show_summary(metrics, vault)
    timeline = metrics["timeline"]

    # Step 0
    assert step0["topics"] == {"glycemic control": 1, "kidney outcomes": 1, "ozempic safety": 1}
    assert step0["ion"] == {"pick": "General update for endocrinology", "why": "specialty only"}
    # Step 1: label card, picked for kidney outcomes → yes
    assert card1["id"] == label_card["id"]
    assert event_of(timeline, "card_sent", card=card1["id"], topic="kidney outcomes", reason="Claims match label")
    assert step1["topics"] == {"glycemic control": 1, "kidney outcomes": 2, "ozempic safety": 2}
    # Step 2: safety study (never-picked tie-break) → not_interested
    assert card2["id"] == safety_study["id"]
    assert step2["topics"]["ozempic safety"] == 1
    # Step 3: kidney study → yes; offer and block
    assert card3["id"] == kidney_study["id"]
    assert step3["topics"]["kidney outcomes"] == 3
    assert reply3["offer"] == "cardio-kidney-metabolic care"
    assert event_of(
        timeline, "topic_blocked", topic="weight management",
        reason="outside Ozempic approved uses → route to medical information", by="stub",
    )
    # Step 4: offer accepted
    assert step4["topics"]["cardio-kidney-metabolic care"] == 1
    assert step4["ion"] == {"pick": "kidney outcomes content", "why": "top score 3 from replies"}
    # End: metrics and vault
    assert [card["id"] for card in vault] == [label_card["id"], kidney_study["id"]]
    assert metrics["engagement_score"] == 72
    assert metrics["reply_rate"] == 1.0
    assert metrics["yes_rate"] == 0.67
    assert metrics["topics_added"] == 1
    assert metrics["muted"] == 0
    assert metrics["saved"] == 2

    print("\nDEMO PATH OK")


if __name__ == "__main__":
    main()
