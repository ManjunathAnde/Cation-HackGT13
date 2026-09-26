import Panel from "../ui/Panel.jsx";
import ResetDemo from "./ResetDemo.jsx";

export default function DemoControls({ resetNote, onResetResult }) {
  return (
    <Panel className="demo-controls" aria-label="Demo controls">
      <h2 className="console-panel-title">Demo controls</h2>
      <div className="demo-controls__row">
        <ResetDemo note={resetNote} onResult={onResetResult} />
        <a className="secondary-button" href="/phone/brief" target="_blank" rel="noopener noreferrer">
          Open Dr. Patel's phone ↗
        </a>
      </div>
    </Panel>
  );
}
