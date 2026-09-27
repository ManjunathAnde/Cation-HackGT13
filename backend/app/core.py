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
# Per-specialty topics, conditions, blocked topics (§6). explorer_candidates and fallback are DORMANT
# since Checkpoint 11e (only llm_check uses them) but still checked at startup.
SPECIALTIES = {
    specialty["value"]: specialty
    for specialty in json.loads((DATA_DIR / "specialties.json").read_text(encoding="utf-8"))["specialties"]
}

SCORE_CHANGE = {"yes": 1, "not_interested": -1, "no_reply": -0.25}
MUTE_AT = -2
RUN_LIMIT = 2  # at most two cards in a row from one topic (§7.3)
YES_STREAK = 2  # two Yes answers in a row trigger a switch to a related topic (§7.3)
RECENT_CARDS = 4  # answered cards shown to the AI at a switch point
# Reasons when plain code chooses the topic (LLM off, or every provider failed)
FALLBACK_REASONS = {
    "run_limit": "Your next highest-scoring topic.",
    "topic_exhausted": "Your next highest-scoring topic.",
    "yes_streak_new": "A new topic related to what you liked.",
    "yes_streak_held": "One of your top-scoring topics.",
}

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
        "picked": [],  # the topic each sent card was picked for, in send order
        "replies": [],  # card answers in order (parallel to "answered")
        "streak_from": 0,  # len(replies) at the last switch: the Yes streak counts from here
        "run_related": None,  # {"topics", "reason"} for cards in a run started by a Yes-streak switch
        "pending_offer": None,  # kept for /topic-reply compatibility; nothing creates offers since 11e
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


def active_topics(doctor):
    return [topic for topic in doctor["topics"] if topic not in doctor["muted"]]


def topic_cards(doctor, topic):
    """Unsent, unblocked cards for `topic`, in cache order (label cards only where allowed)."""
    labels_allowed = config_of(doctor)["label_cards"]
    return [
        card for card in candidates(doctor)
        if topic in card["topics"] and (labels_allowed or card["kind"] != "label")
    ]


def first_passing(doctor, cards):
    """(card, guard reason) for the first card that passes the guard; failures are blocked and logged."""
    config = config_of(doctor)
    for card in cards:
        passed, reason = guard(card, config)
        if passed:
            return card, reason
        doctor["blocked"].append(card["id"])
        log(doctor["id"], "card_blocked", card=card["id"], reason=reason)
    return None, None


def current_run(doctor):
    """(topic of the last sent card, how many cards in a row it has had), or (None, 0)."""
    if not doctor["picked"]:
        return None, 0
    topic = doctor["picked"][-1]
    length = 0
    for picked in reversed(doctor["picked"]):
        if picked != topic:
            break
        length += 1
    return topic, length


def yes_streak(doctor):
    """Yes answers in a row since the last switch."""
    streak = 0
    for answer in reversed(doctor["replies"][doctor["streak_from"]:]):
        if answer != "yes":
            break
        streak += 1
    return streak


def pick_and_send(doctor, trigger):
    """Send the next card (§7.3); `trigger` is how it is sent (auto or manual). None if nothing is left.
    1. A label card first where allowed. 2. No card sent yet: today's ranking, no AI.
    3. Within a run (at most RUN_LIMIT in a row), the same topic. 4. At a switch point, choose a topic."""
    card, reason = first_passing(doctor, topic_label_cards(doctor))
    if card:
        doctor["run_related"] = None
        return send(doctor, card, card["topics"][0], reason, trigger)
    topic, length = current_run(doctor)
    if topic is None:
        return send_first(doctor, trigger)
    switch = "yes_streak" if yes_streak(doctor) >= YES_STREAK else "run_limit" if length >= RUN_LIMIT else None
    if switch is None:
        card, reason = first_passing(doctor, topic_cards(doctor, topic)) if topic not in doctor["muted"] else (None, None)
        if card:
            return send(doctor, card, topic, reason, trigger, doctor["run_related"])
        switch = "topic_exhausted"
    return switch_topic(doctor, switch, topic, length, trigger)


def topic_label_cards(doctor):
    """Unsent label cards with an unmuted doctor topic (only where label cards are allowed)."""
    if not config_of(doctor)["label_cards"]:
        return []
    active = set(active_topics(doctor))
    return [card for card in candidates(doctor) if card["kind"] == "label" and active.intersection(card["topics"])]


def send_first(doctor, trigger):
    """The first card when no label card applies: today's topic ranking, no AI (§7.3)."""
    for topic in rank_topics(doctor):
        card, reason = first_passing(doctor, topic_cards(doctor, topic))
        if card:
            return send(doctor, card, topic, reason, trigger)
    return None


def switch_candidates(doctor, current, length):
    """Unmuted doctor topics plus the specialty's other topics, with unsent cards, not blocked, and not
    a third card in a row (§7.3)."""
    config = config_of(doctor)
    others = [topic for topic in topic_values(config) if topic not in doctor["topics"]]
    return [
        topic for topic in active_topics(doctor) + others
        if topic not in config["blocked"] and topic_cards(doctor, topic)
        and not (topic == current and length >= RUN_LIMIT)
    ]


def fallback_order(doctor, allowed, current, switch):
    """Plain-code order: highest score (topics not held count as 0), then least recently picked, then
    name; other than the current topic unless nothing else is left. After a Yes streak, topics the
    doctor doesn't hold come first."""
    last_picked = doctor["last_picked"]
    others = [topic for topic in allowed if topic != current] or list(allowed)
    order = sorted(others, key=lambda t: (-doctor["topics"].get(t, 0), t in last_picked, last_picked.get(t, 0), t))
    if switch == "yes_streak":
        order = [t for t in order if t not in doctor["topics"]] + [t for t in order if t in doctor["topics"]]
    return order


def recent_cards(doctor):
    """The last RECENT_CARDS answered cards as (title, topic picked for, answer), for the AI."""
    cards = []
    for card_id, answer in zip(doctor["answered"][-RECENT_CARDS:], doctor["replies"][-RECENT_CARDS:]):
        topic = doctor["picked"][doctor["sent"].index(card_id)]
        cards.append({"title": CARDS_BY_ID[card_id]["title"], "topic": topic, "answer": answer})
    return cards


def switch_topic(doctor, switch, current, length, trigger):
    """A switch point: the AI chooses among validated candidates; plain code falls back (§7.3, §8).
    Logs topic_chosen, adds a topic the doctor doesn't hold at score 1, then sends from it."""
    config = config_of(doctor)
    allowed = switch_candidates(doctor, current, length)
    order = fallback_order(doctor, allowed, current, switch)
    tried = []
    chosen, reason, by, rejected = llm.choose_topic(
        doctor["specialty"], recent_cards(doctor), dict(doctor["topics"]), allowed,
        list(config["blocked"]), switch == "yes_streak", tried=tried,
    )
    for topic, provider in rejected:
        log(doctor["id"], "topic_blocked", topic=topic, reason=config["blocked"][topic],
            by=provider, providers_tried=tried)
    for topic in ([chosen] if chosen else []) + [t for t in order if t != chosen]:
        card, guard_reason = first_passing(doctor, topic_cards(doctor, topic))
        if card:
            break
    else:
        return None  # no candidate has a card that passes the guard: nothing is sent
    if topic != chosen:
        by = "fallback"
        reason = FALLBACK_REASONS[switch if switch != "yes_streak" else
                                  "yes_streak_new" if topic not in doctor["topics"] else "yes_streak_held"]
    liked = []
    for picked in doctor["picked"][-YES_STREAK:]:
        if picked not in liked:
            liked.append(picked)
    if topic not in doctor["topics"]:
        doctor["topics"][topic] = 1
        doctor["added"].append(topic)
    doctor["run_related"] = {"topics": liked, "reason": reason} if switch == "yes_streak" else None
    doctor["streak_from"] = len(doctor["replies"])
    log(doctor["id"], "topic_chosen", topic=topic, reason=reason, by=by, providers_tried=tried, trigger=switch)
    return send(doctor, card, topic, guard_reason, trigger, doctor["run_related"])


def waiting_reason(doctor):
    """Why nothing can be sent right now, or None."""
    if doctor["last_card_id"] and doctor["last_card_id"] not in doctor["answered"]:
        return "Doctor has an unanswered card"
    if doctor["pending_offer"]:
        return "Doctor has a pending topic offer"
    return None


def next_card(doctor_id):
    """POST /send: the operator's manual send (same picker as auto-send)."""
    doctor = get_doctor(doctor_id)
    reason = waiting_reason(doctor)
    if reason:
        raise BadRequest(reason)
    return pick_and_send(doctor, "manual")


def send(doctor, card, topic, reason, trigger, related=None):
    doctor["sent"].append(card["id"])
    doctor["picked"].append(topic)
    doctor["last_picked"][topic] = len(doctor["sent"])
    doctor["last_card_id"] = card["id"]
    details = {"related": related} if related else {}
    log(doctor["id"], "card_sent", card=card["id"], title=card["title"], topic=topic, reason=reason,
        trigger=trigger, **details)
    return dict(card)


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
    doctor["replies"].append(answer)
    update_scores(doctor, card, answer)
    log(doctor_id, "reply", card=card_id, answer=answer, scores=dict(doctor["topics"]))
    mute_low_topics(doctor, card)
    if answer == "yes" and card_id not in doctor["vault"]:
        doctor["vault"].append(card_id)
    result = {"offer": None, "ion": ion(doctor)}  # nothing creates offers since Checkpoint 11e
    auto_send(doctor)
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


# ---------- topic offers (compatibility only: nothing creates offers since Checkpoint 11e) ----------

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
            messages.append({"type": "card", "t": event["t"], "card": card, "answer": None,
                             "related": event.get("related")})
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
