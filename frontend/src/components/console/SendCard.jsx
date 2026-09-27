import { useState } from "react";
import { api } from "../../api.js";
import Panel from "../ui/Panel.jsx";
import PrimaryButton from "../ui/PrimaryButton.jsx";
import { topicLabel } from "../../format.js";
import { useTopicLabels } from "../../specialties.js";

function statusLine(inbox, name, labels) {
  if (!inbox) return "Checking…";
  const active = inbox.active;
  if (!active) return "Ready to send";
  if (active.type === "card") return `Waiting for ${name}'s reply to: ${active.card.title}`;
  return `Waiting for ${name}'s answer: ${topicLabel(active.topic, labels)}?`;
}

function resultOf(response) {
  if (response.ok) {
    const card = response.data.card;
    return card ? { ok: true, text: `Sent: ${card.title}` } : { ok: true, text: "No more cards to send." };
  }
  if (response.status === 0) return { ok: false, text: "Can't reach Cation. Is the backend running?" };
  return { ok: false, text: response.data.detail };
}

// inbox: last GET /inbox response (null until the first one arrives).
export default function SendCard({ doctorId, name, inbox, onSent }) {
  const labels = useTopicLabels();
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const waiting = !inbox || inbox.active !== null;

  async function send() {
    setSending(true);
    const response = await api("POST", `/send/${doctorId}`);
    setSending(false);
    setResult(resultOf(response));
    onSent();
  }

  return (
    <Panel className="send-card" aria-label="Send next card (manual override)">
      <h2 className="console-panel-title">Send next card (manual override)</h2>
      <p className="send-card__hint">Cards are sent automatically after each answer.</p>
      <p className={`send-card__status${waiting ? " send-card__status--waiting" : ""}`} role="status">
        {statusLine(inbox, name, labels)}
      </p>
      <PrimaryButton type="button" onClick={send} disabled={sending || waiting}>
        {sending ? "Sending…" : "Send next card"}
      </PrimaryButton>
      {result && <p className={`console-note console-note--${result.ok ? "ok" : "error"}`}>{result.text}</p>}
    </Panel>
  );
}
