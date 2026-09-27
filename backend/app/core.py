"""Cation intelligence layer. Every decision lives here (blueprint §7).

Doctor state and the event log are kept in memory only and reset on restart.
"""

import json
import os
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app import llm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LABEL = json.loads((DATA_DIR / "label.json").read_text(encoding="utf-8"))
CARDS = json.loads((DATA_DIR / "cache.json").read_text(encoding="utf-8"))["cards"]
CARDS_BY_ID = {card["id"]: card for card in CARDS}
LABEL_SENTENCES = {sentence.strip() for sentence in LABEL["sentences"]}
# Per-specialty topics, conditions, explorer candidates, blocked topics, fallback (§6)
SPECIALTIES = {
    specialty["value"]: specialty
    for specialty in json.loads((DATA_DIR / "specialties.json").read_text(encoding="utf-8"))["specialties"]
}

SCORE_CHANGE = {"yes": 1, "not_interested": -1, "no_reply": -0.25}
MUTE_AT = -2
EXPLORE_AT = 3

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


# ---------- specialties ----------

def topic_values(config):
    return [topic["value"] for topic in config["topics"]]


def condition_topics(config):
    return {condition["value"]: condition["topic"] for condition in config["conditions"]}


def check_specialties():
    """Stop at startup if specialties.json is inconsistent (§6)."""
    for value, config in SPECIALTIES.items():
        topics = topic_values(config)
        problems = [
            not set(condition_topics(config).values()) <= set(topics) and "a condition maps to an unknown topic",
            config["explorer_candidates"] != topics + list(config["blocked"])
            and "explorer candidates must be the topics, then the blocked topics",
            not set(config["fallback"]) <= set(config["explorer_candidates"]) and "fallback outside the candidates",
        ]
        if config["label_cards"] and topics != LABEL["approved_topics"]:
            problems.append("topics must equal label.json approved_topics")
        problems = [problem for problem in problems if problem]
        if problems:
            raise ValueError(f"specialties.json, {value}: {'; '.join(problems)}")


check_specialties()


def specialty_config(specialty):
    """The configured specialty for this value (trimmed, case-insensitive), else 422."""
    config = SPECIALTIES.get(specialty.strip().lower())
    if config is None:
        raise Invalid(f"Unsupported specialty: {specialty}")
    return config


def config_of(doctor):
    return SPECIALTIES[doctor["specialty_key"]]


def specialties():
    """GET /specialties: each specialty with its conditions and topics (value + label), for the entry page."""
    return [
        {
            "value": config["value"],
            "label": config["label"],
            "conditions": [{"value": c["value"], "label": c["label"]} for c in config["conditions"]],
            "topics": [{"value": t["value"], "label": t["label"]} for t in config["topics"]],
        }
        for config in SPECIALTIES.values()
    ]


# ---------- onboarding and profile ----------

def onboard(doctor_id, name, specialty, conditions, interests, frequency):
    config = specialty_config(specialty)
    mapped = condition_topics(config)
    for condition in conditions:
        if condition not in mapped:
            raise Invalid(f"Unknown condition: {condition}")
    for interest in interests:
        if interest not in topic_values(config):
            raise Invalid(f"Interest is not an approved topic: {interest}")

    starting = [mapped[condition] for condition in conditions] + list(interests)
    forget_events(doctor_id)  # re-onboarding resets the doctor, including their thread
    DOCTORS[doctor_id] = {
        "id": doctor_id,
        "name": name,
        "specialty": specialty,  # stored as sent (shown in ION and sent to the LLM)
        "specialty_key": config["value"],
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
    result = profile(doctor_id)
    auto_send(DOCTORS[doctor_id])
    return result


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

def guard(card, config):
    """Return (passed, reason). Every claim must equal a label sentence (§7.4).
    A specialty without label cards has no label, so any claim is blocked."""
    sentences = LABEL_SENTENCES if config["label_cards"] else set()
    for claim in card["claims"]:
        if claim.strip() not in sentences:
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
    """Yield (card, picked-for topic) in the order the picker tries them (§7.3).
    Label cards only for specialties that allow them."""
    labels_allowed = config_of(doctor)["label_cards"]
    active = set(rank_topics(doctor))
    if labels_allowed:
        for card in candidates(doctor):
            if card["kind"] == "label" and active.intersection(card["topics"]):
                yield card, card["topics"][0]
    for topic in rank_topics(doctor):
        for card in candidates(doctor):
            if topic in card["topics"] and (labels_allowed or card["kind"] != "label"):
                yield card, topic


def waiting_reason(doctor):
    """Why nothing can be sent right now, or None."""
    if doctor["last_card_id"] and doctor["last_card_id"] not in doctor["answered"]:
        return "Doctor has an unanswered card"
    if doctor["pending_offer"]:
        return "Doctor has a pending topic offer"
    return None


def next_card(doctor_id):
    """POST /send: the operator's manual send."""
    doctor = get_doctor(doctor_id)
    reason = waiting_reason(doctor)
    if reason:
        raise BadRequest(reason)
    return pick_and_send(doctor, "manual")


def pick_and_send(doctor, trigger):
    """Send the first picked card that passes the guard; blocked cards are logged. None if no card is left."""
    for card, topic in pick_order(doctor):
        passed, reason = guard(card, config_of(doctor))
        if not passed:
            doctor["blocked"].append(card["id"])
            log(doctor["id"], "card_blocked", card=card["id"], reason=reason)
            continue
        send(doctor, card, topic, reason, trigger)
        return dict(card)
    return None


def send(doctor, card, topic, reason, trigger):
    doctor["sent"].append(card["id"])
    doctor["last_picked"][topic] = len(doctor["sent"])
    doctor["last_card_id"] = card["id"]
    log(doctor["id"], "card_sent", card=card["id"], title=card["title"], topic=topic, reason=reason, trigger=trigger)


# ---------- automatic sending ----------

def auto_send_on():
    """AUTO_SEND=off turns automatic sending off; unset or any other value means on."""
    return os.getenv("AUTO_SEND", "on").strip().lower() != "off"


def auto_send(doctor):
    """After onboarding and each answer: send the next card, unless something is still waiting."""
    if auto_send_on() and waiting_reason(doctor) is None:
        pick_and_send(doctor, "auto")


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
    result = {"offer": offer, "ion": ion(doctor)}
    auto_send(doctor)  # skipped while the offer is pending
    return result


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
    config = config_of(doctor)
    for topic in card["topics"]:
        if topic not in doctor["topics"] or topic in doctor["explored"]:
            continue
        if doctor["topics"][topic] < EXPLORE_AT:
            continue
        doctor["explored"].append(topic)
        tried = []
        suggestions, by = llm.suggest_related(
            doctor["specialty"], topic, list(doctor["topics"]), config["explorer_candidates"],
            config["fallback"], tried=tried,
        )
        offer = offer_from(doctor, suggestions, by, tried)
        if offer:
            return offer
    return None


def offer_from(doctor, suggestions, by, tried):
    """Plain-code rules applied to the suggestions: skip, block, or offer (§7.5).
    A suggestion outside the specialty's topics is one of its blocked topics (checked at startup)."""
    config = config_of(doctor)
    offer = None
    for topic in suggestions:
        if topic in doctor["topics"]:  # includes muted topics
            continue
        if topic not in topic_values(config):
            log(doctor["id"], "topic_blocked", topic=topic, reason=config["blocked"][topic],
                by=by, providers_tried=tried)
            continue
        if offer is None and doctor["pending_offer"] is None:
            offer = topic
            doctor["pending_offer"] = topic
            log(doctor["id"], "topic_offered", topic=topic, by=by, providers_tried=tried)
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
    result = {"ion": ion(doctor)}
    auto_send(doctor)
    return result


# ---------- mock ION ----------

def ion(doctor):
    if not doctor["answered"]:  # until the first card reply
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
