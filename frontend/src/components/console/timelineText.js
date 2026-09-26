// Display text for the console. Formatting only; the backend decides everything.

export function topicLabel(topic) {
  return topic ? topic.charAt(0).toUpperCase() + topic.slice(1) : "";
}

export function clockTime(seconds) {
  const date = new Date(seconds * 1000);
  return [date.getHours(), date.getMinutes(), date.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}

const BY_LABELS = { redis: "cache (Redis)", gemini: "Gemini", groq: "Groq", fallback: "fixed fallback" };
const REPLY_LABELS = { yes: "Yes, more on this", not_interested: "Not interested", no_reply: "No reply" };
const ANSWER_LABELS = { yes: "Yes", no: "No thanks" };

// Card titles by id, from card_sent events, so replies can name the card.
export function cardTitles(timeline) {
  const titles = {};
  for (const event of timeline) {
    if (event.type === "card_sent") titles[event.card] = event.title;
  }
  return titles;
}

// Returns { text, tone } for one event. tone: "plain", "blocked", "ai" or "safeguard".
export function describe(event, titles) {
  const card = titles[event.card] || event.card;
  switch (event.type) {
    case "onboarded":
      return { text: `Onboarded — topics: ${Object.keys(event.topics || {}).map(topicLabel).join(", ")}`, tone: "plain" };
    case "card_sent":
      return { text: `Sent: ${event.title} (for ${topicLabel(event.topic)}) — ${event.reason}`, tone: "plain" };
    case "card_blocked":
      return { text: `Blocked card ${event.card}: ${event.reason}`, tone: "blocked" };
    case "reply":
      return { text: `Dr. Patel replied ${REPLY_LABELS[event.answer] || event.answer} to ${card}`, tone: "plain" };
    case "topic_muted":
      return { text: `Muted: ${topicLabel(event.topic)}`, tone: "plain" };
    case "topic_offered":
      return { text: `Agent offered: ${topicLabel(event.topic)} — suggested by ${BY_LABELS[event.by] || event.by}`, tone: "ai" };
    case "topic_blocked":
      return { text: `Blocked: ${topicLabel(event.topic)} — ${event.reason}`, tone: "safeguard" };
    case "topic_answer":
      return { text: `Dr. Patel answered ${ANSWER_LABELS[event.answer] || event.answer} to ${topicLabel(event.topic)}`, tone: "plain" };
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
