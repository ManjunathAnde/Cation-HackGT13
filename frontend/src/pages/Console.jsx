import { useEffect, useState } from "react";
import usePoll from "../usePoll.js";
import Panel from "../components/ui/Panel.jsx";
import ConsoleHeader from "../components/console/ConsoleHeader.jsx";
import DemoControls from "../components/console/DemoControls.jsx";
import DoctorSwitcher from "../components/console/DoctorSwitcher.jsx";
import EventTimeline from "../components/console/EventTimeline.jsx";
import IonPanel from "../components/console/IonPanel.jsx";
import MetricsPanel from "../components/console/MetricsPanel.jsx";
import ResetDemo from "../components/console/ResetDemo.jsx";
import SendCard from "../components/console/SendCard.jsx";
import { PRESET_DOCTORS } from "../components/console/doctors.js";
import "./console.css";

function backendState(health) {
  if (health.status === null && !health.reconnecting) return "checking";
  return health.status === 200 && !health.reconnecting ? "up" : "down";
}

// Everything that belongs to one doctor. Console renders it keyed by doctor id, so switching doctors
// starts from empty state with fresh polls, and late answers for the previous doctor are dropped.
function DoctorConsole({ doctorId, preset, onReconnecting }) {
  const inbox = usePoll(`/inbox/${doctorId}`, 2000);
  const profile = usePoll(`/profile/${doctorId}`, 2000);
  const metrics = usePoll(`/metrics/${doctorId}`, 2000);
  const [resets, setResets] = useState(0);
  const [resetNote, setResetNote] = useState(null);

  const name = preset ? preset.name : profile.data ? profile.data.name : doctorId;
  const reconnecting = inbox.reconnecting || profile.reconnecting || metrics.reconnecting;
  const notOnboarded = profile.status === 404 || metrics.status === 404;

  useEffect(() => onReconnecting(reconnecting), [reconnecting, onReconnecting]);

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

  if (notOnboarded) {
    return (
      <Panel className="console__not-onboarded">
        <p className="console__not-onboarded-text">{name} isn't onboarded yet</p>
        {preset && <ResetDemo doctor={preset} note={resetNote} onResult={onResetResult} />}
      </Panel>
    );
  }

  return (
    <>
      <div className="console__grid">
        <div className="console__left">
          <DemoControls
            doctorId={doctorId}
            name={name}
            preset={preset}
            resetNote={resetNote}
            onResetResult={onResetResult}
          />
          <SendCard key={resets} doctorId={doctorId} name={name} inbox={inbox.data} onSent={refreshAll} />
          <IonPanel ion={profile.data ? profile.data.ion : null} />
        </div>
        <div className="console__right">
          <MetricsPanel name={name} metrics={metrics.data} mutedTopics={profile.data ? profile.data.muted : []} />
        </div>
      </div>
      <Panel className="console__timeline">
        <EventTimeline name={name} timeline={metrics.data ? metrics.data.timeline : []} />
      </Panel>
    </>
  );
}

// Impiricus console: the demo operator picks a doctor, sends cards, and Impiricus watches engagement.
export default function Console() {
  const health = usePoll("/health", 10000);
  const [mode, setMode] = useState(PRESET_DOCTORS[0].id);
  const [watchedId, setWatchedId] = useState(null);
  const [reconnecting, setReconnecting] = useState(false);

  const preset = PRESET_DOCTORS.find((doctor) => doctor.id === mode) || null;
  const doctorId = preset ? preset.id : watchedId;

  function chooseMode(next) {
    setMode(next);
    setReconnecting(false);
  }

  function watch(id) {
    setWatchedId(id);
    setReconnecting(false);
  }

  return (
    <div className="console">
      <ConsoleHeader backend={backendState(health)} reconnecting={reconnecting} />
      <DoctorSwitcher mode={mode} watchedId={watchedId} onMode={chooseMode} onWatch={watch} />
      {doctorId ? (
        <DoctorConsole key={doctorId} doctorId={doctorId} preset={preset} onReconnecting={setReconnecting} />
      ) : (
        <Panel className="console__not-onboarded">
          <p className="console__not-onboarded-text">Enter a doctor ID and press Watch.</p>
        </Panel>
      )}
    </div>
  );
}
