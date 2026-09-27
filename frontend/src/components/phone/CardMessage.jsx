import { api } from "../../api.js";
import { useDoctorId } from "../../router.jsx";
import AgentLine from "./AgentLine.jsx";
import AnswerButtons from "./AnswerButtons.jsx";
import ReplyBubble from "./ReplyBubble.jsx";
import ResearchCard from "./ResearchCard.jsx";

const CARD_OPTIONS = [
  { answer: "yes", tone: "yes", label: "Yes, more on this" },
  { answer: "not_interested", tone: "no", label: "Not interested" },
];

// One research card in the Brief. Buttons only when `active` (the API's active item); the answer below when answered.
export default function CardMessage({ message, active, onAnswered }) {
  const { card } = message;
  const doctorId = useDoctorId();

  function submit(answer) {
    return api("POST", "/reply", { doctor_id: doctorId, card_id: card.id, answer });
  }

  return (
    <article className="message" data-card={card.id}>
      <AgentLine>I found this for your brief. Is it relevant to your practice?</AgentLine>
      <ResearchCard card={card} related={message.related}>
        {active && <AnswerButtons options={CARD_OPTIONS} submit={submit} onDone={onAnswered} />}
      </ResearchCard>
      {message.answer && <ReplyBubble type="card" answer={message.answer} />}
    </article>
  );
}
