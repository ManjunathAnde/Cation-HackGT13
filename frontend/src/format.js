// Display formatting shared by the console and the doctor's app.

// The label from GET /specialties when known, else "kidney outcomes" → "Kidney outcomes".
export function topicLabel(topic, labels = {}) {
  if (!topic) return "";
  return labels[topic] || topic.charAt(0).toUpperCase() + topic.slice(1);
}
