import "./ui.css";

// Small inline label. tone: "muted" (grey) or "safeguard" (compliance highlight).
export default function Tag({ tone, children }) {
  return <span className={`tag tag--${tone}`}>{children}</span>;
}
