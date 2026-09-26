import "./ui.css";

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

// Ring gauge for a 0–100 value: thin outer ring, dark track, green arc from 12 o'clock.
export default function RingGauge({ value }) {
  const filled = (Math.min(Math.max(value, 0), 100) / 100) * CIRCUMFERENCE;
  return (
    <div className="ring-gauge" role="img" aria-label={`${value} out of 100`}>
      <svg viewBox="0 0 104 104" aria-hidden="true">
        <circle className="ring-gauge__ring" cx="52" cy="52" r="50" />
        <circle className="ring-gauge__track" cx="52" cy="52" r={RADIUS} />
        <circle
          className="ring-gauge__fill"
          cx="52"
          cy="52"
          r={RADIUS}
          strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
          transform="rotate(-90 52 52)"
        />
      </svg>
      <span className="ring-gauge__label">
        <span className="ring-gauge__value">{value}</span>
        <span className="ring-gauge__max">/100</span>
      </span>
    </div>
  );
}
