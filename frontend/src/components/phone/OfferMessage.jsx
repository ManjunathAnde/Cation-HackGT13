import { api, DOCTOR_ID } from "../../api.js";
import { topicLabel } from "../../format.js";
import AgentLine from "./AgentLine.jsx";
import AnswerButtons from "./AnswerButtons.jsx";
import ReplyBubble from "./ReplyBubble.jsx";

const OFFER_OPTIONS = [
  { answer: "yes", tone: "yes", label: "Yes" },
  { answer: "no", tone: "no", label: "No thanks" },
];

// A related topic the agent offers. Buttons only when `active`; the answer below when answered.
export default function OfferMessage({ message, active, onAnswered }) {
  function submit(answer) {
    return api("POST", "/topic-reply", { doctor_id: DOCTOR_ID, topic: message.topic, answer });
  }

  return (
    <article className="message" data-offer={message.topic}>
      <AgentLine>I found a related topic you might want in your brief.</AgentLine>
      <div className="brief-card brief-card--offer">
        <p className="brief-card__eyebrow">New topic</p>
        <p className="brief-card__offer-text">
          Based on your replies, want updates on {topicLabel(message.topic)} too?
        </p>
        {active && <AnswerButtons options={OFFER_OPTIONS} submit={submit} onDone={onAnswered} />}
      </div>
      {message.answer && <ReplyBubble type="offer" answer={message.answer} />}
    </article>
  );
}
