import SerifHeading from "../ui/SerifHeading.jsx";
import Tag from "../ui/Tag.jsx";
import { cardTitles, clockTime, describe, providersLine } from "./timelineText.js";

// timeline: metrics.timeline (oldest first from the API); shown newest first.
export default function EventTimeline({ timeline }) {
  const titles = cardTitles(timeline);
  const rows = timeline.map((event, index) => ({ event, index })).reverse();
  return (
    <section className="timeline" aria-label="Event timeline">
      <SerifHeading>Event timeline</SerifHeading>
      {rows.length === 0 ? (
        <p className="timeline__empty">No events yet.</p>
      ) : (
        <ol className="timeline__list">
          {rows.map(({ event, index }) => {
            const { text, tone } = describe(event, titles);
            const providers = providersLine(event);
            return (
              <li key={index} className={`timeline__row timeline__row--${tone}`} data-type={event.type}>
                <span className="timeline__dot" aria-hidden="true" />
                <div className="timeline__body">
                  <p className="timeline__text">
                    {text}
                    {tone === "safeguard" && <> <Tag tone="safeguard">Compliance safeguard</Tag></>}
                  </p>
                  {providers && <p className="timeline__providers">{providers}</p>}
                  <time className="timeline__time">{clockTime(event.t)}</time>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
