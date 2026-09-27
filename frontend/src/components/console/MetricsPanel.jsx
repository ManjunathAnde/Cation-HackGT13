import Badge from "../ui/Badge.jsx";
import Eyebrow from "../ui/Eyebrow.jsx";
import RingGauge from "../ui/RingGauge.jsx";
import SerifHeading from "../ui/SerifHeading.jsx";
import StatCard from "../ui/StatCard.jsx";
import Tag from "../ui/Tag.jsx";
import { topicLabel } from "../../format.js";
import { useTopicLabels } from "../../specialties.js";

const MUTE_AT = -2;

function signalLabel(score) {
  if (score >= 70) return "High signal";
  if (score >= 40) return "Building signal";
  return "Early signal";
}

function percent(rate) {
  return `${Math.round(rate * 100)}%`;
}

// Absolute value with up to 2 decimals and a typographic minus: 3, 1.75, −0.25.
function formatScore(score) {
  const text = String(Math.round(Math.abs(score) * 100) / 100);
  return score < 0 ? `−${text}` : text;
}

function EngagementCard({ score }) {
  return (
    <div className="engagement-card">
      <div className="engagement-card__main">
        <div>
          <p className="engagement-card__label">Engagement score</p>
          <p className="engagement-card__score">{score}</p>
          <p className="engagement-card__signal">{signalLabel(score)}</p>
        </div>
        <RingGauge value={score} />
      </div>
      <p className="engagement-card__formula">
        reply rate × 40 + yes rate × 40 + 5 per topic added (max 20) − 10 per muted topic
      </p>
    </div>
  );
}

function ScoreRows({ scores, mutedTopics }) {
  const labels = useTopicLabels();
  const rows = Object.entries(scores).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  if (rows.length === 0) return <p className="scores__empty">No topics yet.</p>;
  const scale = Math.max(3, ...rows.map(([, score]) => score));
  return (
    <ul className="scores" aria-label="Current scores">
      {rows.map(([topic, score]) => {
        const muted = mutedTopics.includes(topic) || score <= MUTE_AT;
        return (
          <li key={topic} className={muted ? "scores__row scores__row--muted" : "scores__row"}>
            <div className="scores__head">
              <span className="scores__topic">
                {topicLabel(topic, labels)}
                {muted && <> <Tag tone="muted">Muted</Tag></>}
              </span>
              <span className="scores__value">{formatScore(score)}</span>
            </div>
            <div className="scores__track">
              <div className="scores__fill" style={{ width: `${(Math.max(0, score) / scale) * 100}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

// name: the doctor's display name; metrics: GET /metrics response (null until loaded); mutedTopics: profile.muted.
export default function MetricsPanel({ name, metrics, mutedTopics }) {
  return (
    <section className="metrics" aria-label="Metrics">
      <Eyebrow>Learning signal</Eyebrow>
      <SerifHeading as="h1" size="page">{name}'s metrics</SerifHeading>
      <p className="metrics__subtitle">How the brief is adapting to their replies.</p>
      {!metrics ? (
        <p className="metrics__loading">Loading metrics…</p>
      ) : (
        <>
          <EngagementCard score={metrics.engagement_score} />
          <div className="metrics__stats metrics__stats--two">
            <StatCard
              label="Reply rate"
              value={percent(metrics.reply_rate)}
              caption={metrics.reply_rate === 1 ? "Every card rated" : "Of cards answered"}
            />
            <StatCard
              label="Yes rate"
              value={percent(metrics.yes_rate)}
              caption={metrics.yes_rate >= 0.6 ? "Strong relevance" : "Still tuning"}
            />
          </div>
          <div className="metrics__stats metrics__stats--three">
            <StatCard label="Topics added" value={metrics.topics_added} />
            <StatCard label="Muted" value={metrics.muted} />
            <StatCard label="Saved to vault" value={metrics.saved} />
          </div>
          <div className="metrics__scores-head">
            <SerifHeading>Current scores</SerifHeading>
            <Badge>Live</Badge>
          </div>
          <ScoreRows scores={metrics.scores} mutedTopics={mutedTopics} />
        </>
      )}
    </section>
  );
}
