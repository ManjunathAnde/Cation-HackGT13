import "./ui.css";

// Radio-style options on the left, a caption for the selected option on the right.
export default function SegmentedControl({ label, options, value, onChange }) {
  const selected = options.find((option) => option.value === value);

  function onKeyDown(event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const index = options.findIndex((option) => option.value === value);
    const step = event.key === "ArrowRight" ? 1 : -1;
    onChange(options[(index + step + options.length) % options.length].value);
  }

  return (
    <div className="segmented">
      <div className="segmented__options" role="radiogroup" aria-label={label} onKeyDown={onKeyDown}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={option.value === value}
            tabIndex={option.value === value ? 0 : -1}
            className="segmented__option"
            onClick={() => onChange(option.value)}
          >
            <span className="segmented__dot" aria-hidden="true" />
            {option.label}
          </button>
        ))}
      </div>
      <span className="segmented__caption">{selected?.caption}</span>
    </div>
  );
}
