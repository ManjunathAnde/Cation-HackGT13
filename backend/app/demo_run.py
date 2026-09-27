"""Replay Dr. Patel's demo path (blueprint §12, Checkpoint 11e picker) through core.py, no UI.

Run from backend/:  python -m app.demo_run
Works with AUTO_SEND on (default: cards arrive after onboarding and each answer) or off
(each card is sent by hand, as POST /send does). The path is the same in both modes.
"""

import os
import sys

# The §12 path is fixed only with the LLM off; set before importing core so .env can't override it.
os.environ["LLM_MODE"] = "off"

from app import core  # noqa: E402

DOCTOR = "dr_patel"
GENERAL_ION = {"pick": "General update for endocrinology", "why": "specialty only"}
NEW_RELATED = "A new topic related to what you liked."
TOP_TOPIC = "One of your top-scoring topics."

# §12: (card, topic it was picked for, answer, related topics or None)
PATH = [
    ("label-ozempic-ckd", "kidney outcomes", "yes", None),
    ("pm-41644273", "kidney outcomes", "not_interested", None),
    ("pm-42594084", "ozempic safety", "yes", None),
    ("pm-39964295", "ozempic safety", "yes", None),
    ("pm-42233552", "cardio-kidney-metabolic care", "yes", ["ozempic safety"]),
    ("pm-39211948", "cardio-kidney-metabolic care", "yes", ["ozempic safety"]),
    ("pm-27633186", "cardiovascular outcomes", "yes", ["cardio-kidney-metabolic care"]),
    ("pm-39210781", "cardiovascular outcomes", "yes", ["cardio-kidney-metabolic care"]),
    ("pm-38787986", "ozempic safety", "yes", ["cardiovascular outcomes"]),
    ("pm-40437949", "ozempic safety", "yes", ["cardiovascular outcomes"]),
]
# §12 switch points: (topic chosen, trigger, reason). LLM off, so every choice is the fallback's.
SWITCHES = [
    ("ozempic safety", "run_limit", "Your next highest-scoring topic."),
    ("cardio-kidney-metabolic care", "yes_streak", NEW_RELATED),
    ("cardiovascular outcomes", "yes_streak", NEW_RELATED),
    ("ozempic safety", "yes_streak", TOP_TOPIC),
    ("cardio-kidney-metabolic care", "yes_streak", TOP_TOPIC),
]
WAITING_AT_END = "pm-39217553"


def waiting_card(auto):
    """The card to answer next: already sent automatically, or sent now by hand."""
    if auto:
        active = core.inbox(DOCTOR)["active"]
        assert active is not None and active["type"] == "card", f"no card waiting: {active}"
        return active["card"]
    return core.next_card(DOCTOR)


def show_step(number, card, answer, profile, related):
    print(f"\n== Step {number}: {card['id']} → {answer}")
    print(f"   {card['title']}")
    if related:
        print(f"   related: {related}")
    print(f"   scores: {profile['topics']}")
    print(f"   ION:    {profile['ion']['pick']} ({profile['ion']['why']})")


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
        details = {k: v for k, v in event.items() if k not in ("t", "type", "doctor", "title", "scores")}
        print(f"   +{event['t'] - start:.3f}s  {event['type']:<14} {details}")


def event_of(timeline, event_type, **match):
    return [
        event for event in timeline
        if event["type"] == event_type and all(event.get(k) == v for k, v in match.items())
    ]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    auto = core.auto_send_on()
    trigger = "auto" if auto else "manual"
    print(f"AUTO_SEND {'on' if auto else 'off'}")

    profile = core.onboard(
        doctor_id=DOCTOR,
        name="Dr. Patel",
        specialty="endocrinology",
        conditions=["type 2 diabetes", "chronic kidney disease"],
        interests=["ozempic safety"],
        frequency="weekly",
    )
    print(f"== Step 0: onboard\n   scores: {profile['topics']}\n   ION:    {profile['ion']['pick']}")
    assert profile["topics"] == {"glycemic control": 1, "kidney outcomes": 1, "ozempic safety": 1}
    assert profile["ion"] == GENERAL_ION

    for number, (card_id, _, answer, related_topics) in enumerate(PATH, 1):
        card = waiting_card(auto)
        message = core.inbox(DOCTOR)["active"]
        if number == 1:  # ION stays general until the first card reply, also while card 1 is waiting
            assert core.profile(DOCTOR)["ion"] == GENERAL_ION
        result = core.reply(DOCTOR, card["id"], answer)
        show_step(number, card, answer, core.profile(DOCTOR), message["related"])
        assert card["id"] == card_id, (number, card["id"], card_id)
        assert result["offer"] is None
        assert (message["related"] or {}).get("topics") == related_topics, (number, message["related"])

    metrics = core.metrics(DOCTOR)
    vault = core.vault(DOCTOR)
    show_summary(metrics, vault)
    timeline = metrics["timeline"]

    sent = event_of(timeline, "card_sent")
    picked = [(event["card"], event["topic"]) for event in sent]
    assert picked[:len(PATH)] == [(card_id, topic) for card_id, topic, _, _ in PATH], picked
    assert event_of(timeline, "card_sent", card="label-ozempic-ckd", reason="Claims match label")
    assert [event["trigger"] for event in sent] == [trigger] * len(sent)
    chosen = [(e["topic"], e["trigger"], e["reason"]) for e in event_of(timeline, "topic_chosen")]
    expected_switches = SWITCHES if auto else SWITCHES[:-1]  # manual mode hasn't sent the next card yet
    assert chosen == expected_switches, chosen
    assert all(e["by"] == "fallback" and e["providers_tried"] == [] for e in event_of(timeline, "topic_chosen"))
    assert not event_of(timeline, "topic_offered") and not event_of(timeline, "topic_blocked")
    if auto:
        assert core.inbox(DOCTOR)["active"]["card"]["id"] == WAITING_AT_END
        try:
            core.next_card(DOCTOR)
            raise AssertionError("manual send allowed while a card is waiting")
        except core.BadRequest as err:
            assert str(err) == "Doctor has an unanswered card"
    else:
        assert core.inbox(DOCTOR)["active"] is None
        assert core.next_card(DOCTOR)["id"] == WAITING_AT_END

    assert core.profile(DOCTOR)["ion"] == {"pick": "ozempic safety content", "why": "top score 6 from replies"}
    assert metrics["topics_added"] == 2
    assert metrics["engagement_score"] == 86
    assert metrics["reply_rate"] == 1.0
    assert metrics["yes_rate"] == 0.9
    assert metrics["muted"] == 0
    assert metrics["saved"] == 9
    assert [card["id"] for card in vault] == [c for c, _, a, _ in PATH if a == "yes"]

    print("\nDEMO PATH OK")


if __name__ == "__main__":
    main()
