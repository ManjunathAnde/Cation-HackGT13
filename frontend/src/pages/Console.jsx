import { useState } from "react";
import { DOCTOR_ID } from "../api.js";
import usePoll from "../usePoll.js";
import Panel from "../components/ui/Panel.jsx";
import ConsoleHeader from "../components/console/ConsoleHeader.jsx";
import DemoControls from "../components/console/DemoControls.jsx";
import EventTimeline from "../components/console/EventTimeline.jsx";
import IonPanel from "../components/console/IonPanel.jsx";
import MetricsPanel from "../components/console/MetricsPanel.jsx";
import ResetDemo from "../components/console/ResetDemo.jsx";
import SendCard from "../components/console/SendCard.jsx";
import "./console.css";

function backendState(health) {
  if (health.status === null && !health.reconnecting) return "checking";
  return health.status === 200 && !health.reconnecting ? "up" : "down";
}

// Impiricus console: the demo operator sends cards here and Impiricus watches engagement.
export default function Console() {
  const health = usePoll("/health", 10000);
  const inbox = usePoll(`/inbox/${DOCTOR_ID}`, 2000);
  const profile = usePoll(`/profile/${DOCTOR_ID}`, 2000);
  const metrics = usePoll(`/metrics/${DOCTOR_ID}`, 2000);
  const [resets, setResets] = useState(0);
  const [resetNote, setResetNote] = useState(null);

  const reconnecting = inbox.reconnecting || profile.reconnecting || metrics.reconnecting;
  const notOnboarded = profile.status === 404 || metrics.status === 404;

  function refreshAll() {
    inbox.refresh();
    profile.refresh();
    metrics.refresh();
  }

  function onResetResult(note) {
    setResetNote(note);
    if (!note.ok) return;
    setResets((n) => n + 1);
    refreshAll();
  }

  return (
    <div className="console">
      <ConsoleHeader backend={backendState(health)} reconnecting={reconnecting} />
      {notOnboarded ? (
        <Panel className="console__not-onboarded">
          <p className="console__not-onboarded-text">Dr. Patel isn't onboarded yet</p>
          <ResetDemo note={resetNote} onResult={onResetResult} />
        </Panel>
      ) : (
        <>
          <div className="console__grid">
            <div className="console__left">
              <DemoControls resetNote={resetNote} onResetResult={onResetResult} />
              <SendCard key={resets} inbox={inbox.data} onSent={refreshAll} />
              <IonPanel ion={profile.data ? profile.data.ion : null} />
            </div>
            <div className="console__right">
              <MetricsPanel metrics={metrics.data} mutedTopics={profile.data ? profile.data.muted : []} />
            </div>
          </div>
          <Panel className="console__timeline">
            <EventTimeline timeline={metrics.data ? metrics.data.timeline : []} />
          </Panel>
        </>
      )}
    </div>
  );
}
