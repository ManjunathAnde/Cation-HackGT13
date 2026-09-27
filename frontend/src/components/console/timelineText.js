// Display text for the console. Formatting only; the backend decides everything.
import { topicLabel } from "../../format.js";

export function clockTime(seconds) {
  const date = new Date(seconds * 1000);
  return [date.getHours(), date.getMinutes(), date.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}

const BY_LABELS = { redis: "cache (Redis)", gemini: "Gemini", groq: "Groq", fallback: "fixed fallback" };
const REPLY_LABELS = { yes: "Yes, more on this", not_interested: "Not interested", no_reply: "No reply" };
const ANSWER_LABELS = { yes: "Yes", no: "No thanks" };
const SENT_LABELS = { auto: "Sent automatically", manual: "Sent by operator" };
const SWITCH_LABELS = {
  run_limit: "after 2 in a row",
  yes_streak: "after 2 Yes",
  topic_exhausted: "after the topic ran out",
};

// Card titles by id, from card_sent events, so replies can name the card.
export function cardTitles(timeline) {
  const titles = {};
  for (const event of timeline) {
    if (event.type === "card_sent") titles[event.card] = event.title;
  }
  return titles;
}

// Returns { text, tone } for one event. tone: "plain", "blocked", "ai" or "safeguard".
// name: the doctor's display name; labels: topic → label from GET /specialties (may be empty).
export function describe(event, titles, name, labels) {
  const card = titles[event.card] || event.card;
  const topic = (value) => topicLabel(value, labels);
  switch (event.type) {
    case "onboarded":
      return { text: `Onboarded — topics: ${Object.keys(event.topics || {}).map(topic).join(", ")}`, tone: "plain" };
    case "card_sent":
      if (event.related) return { text: `Sent related: ${event.title}`, tone: "plain" };
      return { text: `${SENT_LABELS[event.trigger] || "Sent"}: ${event.title} (for ${topic(event.topic)}) — ${event.reason}`, tone: "plain" };
    case "topic_chosen":
      return {
        text: `Next topic: ${topic(event.topic)} — ${event.reason} (${SWITCH_LABELS[event.trigger] || event.trigger}, by ${BY_LABELS[event.by] || event.by})`,
        tone: "ai",
      };
    case "card_blocked":
      return { text: `Blocked card ${event.card}: ${event.reason}`, tone: "blocked" };
    case "reply":
      return { text: `${name} replied ${REPLY_LABELS[event.answer] || event.answer} to ${card}`, tone: "plain" };
    case "topic_muted":
      return { text: `Muted: ${topic(event.topic)}`, tone: "plain" };
    case "topic_offered":
      return { text: `Agent offered: ${topic(event.topic)} — suggested by ${BY_LABELS[event.by] || event.by}`, tone: "ai" };
    case "topic_blocked":
      return { text: `Blocked: ${topic(event.topic)} — ${event.reason}`, tone: "safeguard" };
    case "topic_answer":
      return { text: `${name} answered ${ANSWER_LABELS[event.answer] || event.answer} to ${topic(event.topic)}`, tone: "plain" };
    default:
      return { text: event.type, tone: "plain" };
  }
}

// "redis: miss · gemini: ok", or null when there is nothing to show.
export function providersLine(event) {
  const tried = event.providers_tried;
  if (!Array.isArray(tried) || tried.length === 0) return null;
  return tried.map((entry) => `${entry.provider}: ${entry.result}`).join(" · ");
}
