import Panel from "../ui/Panel.jsx";
import ResetDemo from "./ResetDemo.jsx";

// preset: the selected preset doctor (Reset demo), or null when watching another ID (no Reset).
export default function DemoControls({ doctorId, name, preset, resetNote, onResetResult }) {
  return (
    <Panel className="demo-controls" aria-label="Demo controls">
      <h2 className="console-panel-title">Demo controls</h2>
      <div className="demo-controls__row">
        {preset && <ResetDemo doctor={preset} note={resetNote} onResult={onResetResult} />}
        <a
          className="secondary-button"
          href={`/phone/brief?doctor=${encodeURIComponent(doctorId)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open {name}'s phone ↗
        </a>
      </div>
    </Panel>
  );
}
