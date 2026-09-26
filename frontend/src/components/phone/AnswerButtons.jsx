import { useState } from "react";
import ChoiceButton from "../ui/ChoiceButton.jsx";

// Buttons for the active item. options: [{ answer, tone, label }]; submit(answer) → api() result.
// Both buttons disable on click and the clicked one shows "Sending…". On success they stay
// disabled until the refreshed inbox removes them; on error they re-enable with the message.
export default function AnswerButtons({ options, submit, onDone }) {
  const [sending, setSending] = useState(null);
  const [error, setError] = useState(null);

  async function answer(value) {
    setSending(value);
    setError(null);
    const result = await submit(value);
    if (!result.ok) {
      setSending(null);
      setError(result.status === 0 ? "Can't reach Cation. Is the backend running?" : result.data.detail);
    }
    onDone();
  }

  return (
    <div className="answer">
      <div className="answer__buttons">
        {options.map((option) => (
          <ChoiceButton
            key={option.answer}
            tone={option.tone}
            disabled={sending !== null}
            onClick={() => answer(option.answer)}
          >
            {sending === option.answer ? "Sending…" : option.label}
          </ChoiceButton>
        ))}
      </div>
      {error && (
        <p className="answer__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
