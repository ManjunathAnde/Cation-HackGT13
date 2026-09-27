import { useEffect, useRef } from "react";
import { redirect, useDoctorId, withSearch } from "../router.jsx";
import usePoll from "../usePoll.js";
import AgentLine from "../components/phone/AgentLine.jsx";
import CardMessage from "../components/phone/CardMessage.jsx";
import DoctorGate from "../components/phone/DoctorGate.jsx";
import OfferMessage from "../components/phone/OfferMessage.jsx";
import Eyebrow from "../components/ui/Eyebrow.jsx";
import PhoneColumn from "../components/ui/PhoneColumn.jsx";
import SerifHeading from "../components/ui/SerifHeading.jsx";
import TabBar from "../components/ui/TabBar.jsx";
import Wordmark from "../components/ui/Wordmark.jsx";
import "./brief.css";

// The API marks one item as active; only that item gets buttons. This only compares, never decides.
function isActive(message, active) {
  if (!active || active.type !== message.type) return false;
  if (message.type === "card") return message.card.id === active.card.id;
  return message.topic === active.topic;
}

function updatesLine(count) {
  return `${count} ${count === 1 ? "update" : "updates"} · tuned to your interests`;
}

// Scrolls to the bottom on first load and whenever the number of messages grows.
function useScrollOnNewMessage(count, loaded) {
  const seen = useRef(null);
  useEffect(() => {
    if (!loaded) return;
    if (seen.current === null || count > seen.current) {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: seen.current === null ? "auto" : "smooth" });
    }
    seen.current = count;
  }, [count, loaded]);
}

function Thread() {
  const doctorId = useDoctorId();
  const inbox = usePoll(`/inbox/${doctorId}`, 2000);
  const messages = inbox.data ? inbox.data.messages : [];
  const active = inbox.data ? inbox.data.active : null;
  const cardCount = messages.filter((message) => message.type === "card").length;

  useEffect(() => {
    if (inbox.status === 404) redirect(withSearch("/phone/onboard"));
  }, [inbox.status]);
  useScrollOnNewMessage(messages.length, inbox.data !== null);

  return (
    <PhoneColumn withTabBar>
      <div className="brief">
        <Wordmark />
        <header className="brief__header">
          <Eyebrow>Your brief</Eyebrow>
          <SerifHeading as="h1" size="page">
            One useful read.
          </SerifHeading>
          {cardCount > 0 && <p className="brief__subtitle">{updatesLine(cardCount)}</p>}
          {inbox.reconnecting && <p className="brief__reconnecting">reconnecting…</p>}
        </header>
        {inbox.data && messages.length === 0 && (
          <div className="brief__empty">
            <AgentLine>No updates yet. Your first one is on its way.</AgentLine>
          </div>
        )}
        <div className="brief__thread">
          {messages.map((message, index) =>
            message.type === "card" ? (
              <CardMessage
                key={`${index}-${message.card.id}`}
                message={message}
                active={isActive(message, active)}
                onAnswered={inbox.refresh}
              />
            ) : (
              <OfferMessage
                key={`${index}-${message.topic}`}
                message={message}
                active={isActive(message, active)}
                onAnswered={inbox.refresh}
              />
            )
          )}
        </div>
      </div>
      <TabBar />
    </PhoneColumn>
  );
}

// The doctor's brief: the conversation thread at /phone/brief.
export default function Brief() {
  return (
    <DoctorGate>
      <Thread />
    </DoctorGate>
  );
}
