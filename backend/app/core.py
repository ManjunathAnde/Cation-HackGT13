"""Cation intelligence layer. Every decision lives here (blueprint §7).

Doctor state and the event log are kept in memory only and reset on restart.
"""

import json
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LABEL = json.loads((DATA_DIR / "label.json").read_text(encoding="utf-8"))
CARDS = json.loads((DATA_DIR / "cache.json").read_text(encoding="utf-8"))["cards"]
CARDS_BY_ID = {card["id"]: card for card in CARDS}

APPROVED_TOPICS = LABEL["approved_topics"]
LABEL_SENTENCES = {sentence.strip() for sentence in LABEL["sentences"]}
CONDITION_TOPICS = {
    "type 2 diabetes": "glycemic control",
    "chronic kidney disease": "kidney outcomes",
}

SCORE_CHANGE = {"yes": 1, "not_interested": -1, "no_reply": -0.25}
MUTE_AT = -2
EXPLORE_AT = 3

# Fixed explorer suggestions until the LLM arrives in Checkpoint 10.
EXPLORER_STUB = ["cardio-kidney-metabolic care", "weight management"]
EXPLORER_BY = "stub"
BLOCKED_TOPIC_REASON = "outside Ozempic approved uses → route to medical information"

DOCTORS = {}
EVENTS = []


class NotFound(Exception):
    """Unknown doctor (API: 404)."""


class BadRequest(Exception):
    """Reply or topic reply that is not allowed right now (API: 400)."""


class Invalid(Exception):
    """Onboarding validation failure (API: 422)."""


# ---------- event log ----------

def log(doctor_id, event_type, **details):
    EVENTS.append({"t": time.time(), "type": event_type, "doctor": doctor_id, **details})


def doctor_events(doctor_id):
    return [event for event in EVENTS if event["doctor"] == doctor_id]


def forget_events(doctor_id):
    EVENTS[:] = [event for event in EVENTS if event["doctor"] != doctor_id]


def events(since=0):
    return [event for event in EVENTS if event["t"] > since]


# ---------- onboarding and profile ----------

def onboard(doctor_id, name, specialty, conditions, interests, frequency):
    for condition in conditions:
        if condition not in CONDITION_TOPICS:
            raise Invalid(f"Unknown condition: {condition}")
    for interest in interests:
        if interest not in APPROVED_TOPICS:
            raise Invalid(f"Interest is not an approved topic: {interest}")

    starting = [CONDITION_TOPICS[condition] for condition in conditions] + list(interests)
    forget_events(doctor_id)  # re-onboarding resets the doctor, including their thread
    DOCTORS[doctor_id] = {
        "id": doctor_id,
        "name": name,
        "specialty": specialty,
        "conditions": list(conditions),
        "interests": list(interests),
        "frequency": frequency,
        "topics": {topic: 1 for topic in starting},
        "muted": [],
        "sent": [],
        "blocked": [],
        "last_card_id": None,
        "answered": [],
        "last_picked": {},
        "explored": [],
        "pending_offer": None,
        "added": [],
        "vault": [],
    }
    log(doctor_id, "onboarded", topics=dict(DOCTORS[doctor_id]["topics"]))
    return profile(doctor_id)


def get_doctor(doctor_id):
    if doctor_id not in DOCTORS:
        raise NotFound(f"Unknown doctor: {doctor_id}")
    return DOCTORS[doctor_id]


def profile(doctor_id):
    doctor = get_doctor(doctor_id)
    return {
        "id": doctor["id"],
        "name": doctor["name"],
        "specialty": doctor["specialty"],
        "conditions": list(doctor["conditions"]),
        "interests": list(doctor["interests"]),
        "frequency": doctor["frequency"],
        "topics": dict(doctor["topics"]),
        "muted": list(doctor["muted"]),
        "ion": ion(doctor),
    }


# ---------- guard and picker ----------

def guard(card):
    """Return (passed, reason). Every claim must equal a label sentence (§7.4)."""
    for claim in card["claims"]:
        if claim.strip() not in LABEL_SENTENCES:
            return False, f"Unsupported claim: {claim}"
    if card["claims"]:
        return True, "Claims match label"
    return True, "Title + link only"


def rank_topics(doctor):
    """Unmuted topics: highest score, then never picked, then oldest pick, then name (§7.3)."""
    last_picked = doctor["last_picked"]
    active = [topic for topic in doctor["topics"] if topic not in doctor["muted"]]
    return sorted(
        active,
        key=lambda topic: (
            -doctor["topics"][topic],
            topic in last_picked,
            last_picked.get(topic, 0),
            topic,
        ),
    )


def candidates(doctor):
    return [
        card for card in CARDS
        if card["id"] not in doctor["sent"] and card["id"] not in doctor["blocked"]
    ]


def pick_order(doctor):
    """Yield (card, picked-for topic) in the order the picker tries them (§7.3)."""
    active = set(rank_topics(doctor))
    for card in candidates(doctor):
        if card["kind"] == "label" and active.intersection(card["topics"]):
            yield card, card["topics"][0]
    for topic in rank_topics(doctor):
        for card in candidates(doctor):
            if topic in card["topics"]:
                yield card, topic


def next_card(doctor_id):
    doctor = get_doctor(doctor_id)
    if doctor["last_card_id"] and doctor["last_card_id"] not in doctor["answered"]:
        raise BadRequest("Doctor has an unanswered card")
    if doctor["pending_offer"]:
        raise BadRequest("Doctor has a pending topic offer")
    for card, topic in pick_order(doctor):
        passed, reason = guard(card)
        if not passed:
            doctor["blocked"].append(card["id"])
            log(doctor_id, "card_blocked", card=card["id"], reason=reason)
            continue
        send(doctor, card, topic, reason)
        return dict(card)
    return None


def send(doctor, card, topic, reason):
    doctor["sent"].append(card["id"])
    doctor["last_picked"][topic] = len(doctor["sent"])
    doctor["last_card_id"] = card["id"]
    log(doctor["id"], "card_sent", card=card["id"], title=card["title"], topic=topic, reason=reason)


# ---------- scorer ----------

def reply(doctor_id, card_id, answer):
    doctor = get_doctor(doctor_id)
    if answer not in SCORE_CHANGE:
        raise BadRequest(f"Unknown answer: {answer}")
    if card_id != doctor["last_card_id"] or card_id in doctor["answered"]:
        raise BadRequest(f"Card {card_id} is not awaiting a reply")

    card = CARDS_BY_ID[card_id]
    doctor["answered"].append(card_id)
    update_scores(doctor, card, answer)
    log(doctor_id, "reply", card=card_id, answer=answer, scores=dict(doctor["topics"]))
    mute_low_topics(doctor, card)
    if answer == "yes" and card_id not in doctor["vault"]:
        doctor["vault"].append(card_id)
    offer = explore(doctor, card)
    return {"offer": offer, "ion": ion(doctor)}


def update_scores(doctor, card, answer):
    for topic in card["topics"]:
        if topic in doctor["topics"]:
            doctor["topics"][topic] += SCORE_CHANGE[answer]


def mute_low_topics(doctor, card):
    for topic in card["topics"]:
        if topic in doctor["topics"] and doctor["topics"][topic] <= MUTE_AT and topic not in doctor["muted"]:
            doctor["muted"].append(topic)
            log(doctor["id"], "topic_muted", topic=topic)


# ---------- explorer ----------

def explore(doctor, card):
    """Check the replied card's topics; return the offered topic or None (§7.5)."""
    for topic in card["topics"]:
        if topic not in doctor["topics"] or topic in doctor["explored"]:
            continue
        if doctor["topics"][topic] < EXPLORE_AT:
            continue
        doctor["explored"].append(topic)
        offer = offer_from(doctor, EXPLORER_STUB)
        if offer:
            return offer
    return None


def offer_from(doctor, suggestions):
    offer = None
    for topic in suggestions:
        if topic in doctor["topics"]:  # includes muted topics
            continue
        if topic not in APPROVED_TOPICS:
            log(doctor["id"], "topic_blocked", topic=topic, reason=BLOCKED_TOPIC_REASON, by=EXPLORER_BY)
            continue
        if offer is None and doctor["pending_offer"] is None:
            offer = topic
            doctor["pending_offer"] = topic
            log(doctor["id"], "topic_offered", topic=topic, by=EXPLORER_BY)
    return offer


def topic_reply(doctor_id, topic, answer):
    doctor = get_doctor(doctor_id)
    if answer not in ("yes", "no"):
        raise BadRequest(f"Unknown answer: {answer}")
    if doctor["pending_offer"] is None or topic != doctor["pending_offer"]:
        raise BadRequest(f"Topic {topic} is not on offer")

    doctor["pending_offer"] = None
    if answer == "yes":
        doctor["topics"][topic] = 1
        doctor["added"].append(topic)
    log(doctor_id, "topic_answer", topic=topic, answer=answer)
    return {"ion": ion(doctor)}


# ---------- mock ION ----------

def ion(doctor):
    if not doctor["sent"]:
        return {"pick": f"General update for {doctor['specialty']}", "why": "specialty only"}
    ranked = rank_topics(doctor)
    if not ranked:
        return {"pick": "No active topics", "why": "all topics muted"}
    top = ranked[0]
    return {"pick": f"{top} content", "why": f"top score {doctor['topics'][top]:g} from replies"}


# ---------- inbox ----------

def inbox(doctor_id):
    """The doctor's thread from the event log, plus the one item awaiting a reply (§10)."""
    get_doctor(doctor_id)
    messages = []
    for event in doctor_events(doctor_id):
        if event["type"] == "card_sent":
            card = dict(CARDS_BY_ID[event["card"]])
            messages.append({"type": "card", "t": event["t"], "card": card, "answer": None})
        elif event["type"] == "reply":
            open_message(messages, "card", lambda m: m["card"]["id"] == event["card"])["answer"] = event["answer"]
        elif event["type"] == "topic_offered":
            messages.append({"type": "offer", "t": event["t"], "topic": event["topic"], "answer": None})
        elif event["type"] == "topic_answer":
            open_message(messages, "offer", lambda m: m["topic"] == event["topic"])["answer"] = event["answer"]
    unanswered = [message for message in messages if message["answer"] is None]
    return {"messages": messages, "active": unanswered[-1] if unanswered else None}


def open_message(messages, message_type, matches):
    """The most recent unanswered message of this type that matches."""
    return next(
        message for message in reversed(messages)
        if message["type"] == message_type and message["answer"] is None and matches(message)
    )


# ---------- vault and metrics ----------

def vault(doctor_id, q=None):
    doctor = get_doctor(doctor_id)
    cards = [dict(CARDS_BY_ID[card_id]) for card_id in doctor["vault"]]
    if not q:
        return cards
    needle = q.lower()
    return [
        card for card in cards
        if needle in card["title"].lower() or any(needle in topic.lower() for topic in card["topics"])
    ]


def round_half_up(value, places=0):
    step = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP))


def metrics(doctor_id):
    doctor = get_doctor(doctor_id)
    timeline = doctor_events(doctor_id)
    answers = [event["answer"] for event in timeline if event["type"] == "reply"]
    replies = len(answers)
    reply_rate = sum(answer != "no_reply" for answer in answers) / replies if replies else 0
    yes_rate = answers.count("yes") / replies if replies else 0

    engagement = (
        reply_rate * 40
        + yes_rate * 40
        + min(len(doctor["added"]) * 5, 20)
        - 10 * len(doctor["muted"])
    )
    engagement = min(max(engagement, 0), 100)

    return {
        "engagement_score": int(round_half_up(engagement)),
        "reply_rate": round_half_up(reply_rate, 2),
        "yes_rate": round_half_up(yes_rate, 2),
        "topics_added": len(doctor["added"]),
        "muted": len(doctor["muted"]),
        "saved": len(doctor["vault"]),
        "scores": dict(doctor["topics"]),
        "timeline": timeline,
    }
