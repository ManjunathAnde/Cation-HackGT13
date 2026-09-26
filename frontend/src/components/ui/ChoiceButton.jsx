import "./ui.css";

// Answer button in the brief. tone: "yes" (green) or "no" (grey).
export default function ChoiceButton({ tone, children, ...props }) {
  return (
    <button type="button" className={`choice-button choice-button--${tone}`} {...props}>
      {children}
    </button>
  );
}
