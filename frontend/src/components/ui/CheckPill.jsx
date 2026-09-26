import "./ui.css";

// Checkbox-pill row: a real checkbox, styled as the design's pill.
export default function CheckPill({ label, checked, onChange }) {
  return (
    <label className={`check-pill ${checked ? "check-pill--checked" : ""}`}>
      <input
        type="checkbox"
        className="check-pill__input"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="check-pill__box" aria-hidden="true">
        {checked ? "✓" : ""}
      </span>
      <span className="check-pill__label">{label}</span>
    </label>
  );
}
