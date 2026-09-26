// Display formatting shared by the console and the doctor's app.

// "kidney outcomes" → "Kidney outcomes"
export function topicLabel(topic) {
  return topic ? topic.charAt(0).toUpperCase() + topic.slice(1) : "";
}
