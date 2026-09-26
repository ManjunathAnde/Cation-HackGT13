import { topicLabel } from "../../format.js";
import "./researchCard.css";

const SOURCE_LABELS = { label: "FDA label · DailyMed", study: "Study · PubMed" };

// A research card as the doctor sees it (Brief and Vault). `children` go under the footer
// (the Brief's answer buttons).
export default function ResearchCard({ card, children }) {
  return (
    <div className="brief-card">
      <div className="brief-card__meta">
        <div className="brief-card__pills">
          {card.topics.map((topic) => (
            <span key={topic} className="topic-pill">
              {topicLabel(topic)}
            </span>
          ))}
        </div>
        <span className="brief-card__source">{SOURCE_LABELS[card.kind]}</span>
      </div>
      <h2 className="brief-card__title">{card.title}</h2>
      {card.kind === "label" &&
        card.claims.map((claim) => (
          <blockquote key={claim} className="brief-card__claim">
            <span className="brief-card__claim-label">FDA label text</span>
            <span className="brief-card__claim-text">{claim}</span>
          </blockquote>
        ))}
      <div className="brief-card__footer">
        <span className="brief-card__summary">{card.summary}</span>
        <a className="brief-card__link" href={card.link} target="_blank" rel="noopener noreferrer">
          Read source ↗
        </a>
      </div>
      {children}
    </div>
  );
}
