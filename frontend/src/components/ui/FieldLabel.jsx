import "./ui.css";

// Label on the left, uppercase meta (e.g. REQUIRED) on the right.
export default function FieldLabel({ htmlFor, id, text, meta }) {
  return (
    <div className="field-label">
      <label className="field-label__text" htmlFor={htmlFor} id={id}>
        {text}
      </label>
      {meta && <span className="field-label__meta">{meta}</span>}
    </div>
  );
}
