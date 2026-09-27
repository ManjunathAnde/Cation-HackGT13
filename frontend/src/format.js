// Display formatting shared by the console and the doctor's app.

// The label from GET /specialties when known, else "kidney outcomes" → "Kidney outcomes".
export function topicLabel(topic, labels = {}) {
  if (!topic) return "";
  return labels[topic] || topic.charAt(0).toUpperCase() + topic.slice(1);
}

// ["A"] → "A", ["A", "B"] → "A and B", ["A", "B", "C"] → "A, B and C"
export function joinWithAnd(items) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
