import "./ui.css";

export default function RemovablePill({ label, onRemove }) {
  return (
    <span className="removable-pill">
      {label}
      <button type="button" className="removable-pill__remove" aria-label={`Remove ${label}`} onClick={onRemove}>
        ×
      </button>
    </span>
  );
}
