import "./ui.css";

export default function StatCard({ label, value, caption }) {
  return (
    <div className="stat-card">
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      {caption && <p className="stat-card__caption">{caption}</p>}
    </div>
  );
}
