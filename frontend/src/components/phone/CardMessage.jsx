import { api, DOCTOR_ID } from "../../api.js";
import { topicLabel } from "../../format.js";
import AgentLine from "./AgentLine.jsx";
import AnswerButtons from "./AnswerButtons.jsx";
import ReplyBubble from "./ReplyBubble.jsx";

const SOURCE_LABELS = { label: "FDA label · DailyMed", study: "Study · PubMed" };

const CARD_OPTIONS = [
  { answer: "yes", tone: "yes", label: "Yes, more on this" },
  { answer: "not_interested", tone: "no", label: "Not interested" },
];

// One research card. Buttons only when `active` (the API's active item); the answer below when answered.
export default function CardMessage({ message, active, onAnswered }) {
  const { card } = message;

  function submit(answer) {
    return api("POST", "/reply", { doctor_id: DOCTOR_ID, card_id: card.id, answer });
  }

  return (
    <article className="message" data-card={card.id}>
      <AgentLine>I found this for your brief. Is it relevant to your practice?</AgentLine>
      <div className="brief-card">
        <div className="brief-card__meta">
          <div className="brief-card__pills">
            {card.topics.map((topic) => (
              <span key={topic} className="topic-pill">
                {topicLabel(topic)}
              </span>
            ))}
          </div>
          <span className="brief-card__source">{SOURCE_LABELS[card.kind]}</span>
        </div>
        <h2 className="brief-card__title">{card.title}</h2>
        {card.kind === "label" &&
          card.claims.map((claim) => (
            <blockquote key={claim} className="brief-card__claim">
              <span className="brief-card__claim-label">FDA label text</span>
              <span className="brief-card__claim-text">{claim}</span>
            </blockquote>
          ))}
        <div className="brief-card__footer">
          <span className="brief-card__summary">{card.summary}</span>
          <a className="brief-card__link" href={card.link} target="_blank" rel="noopener noreferrer">
            Read source ↗
          </a>
        </div>
        {active && <AnswerButtons options={CARD_OPTIONS} submit={submit} onDone={onAnswered} />}
      </div>
      {message.answer && <ReplyBubble type="card" answer={message.answer} />}
    </article>
  );
}
