import Wordmark from "../ui/Wordmark.jsx";

const BACKEND_TEXT = { checking: "Checking backend…", up: "Backend connected", down: "Backend not running" };

// backend: "checking", "up" or "down".
export default function ConsoleHeader({ backend, reconnecting }) {
  return (
    <header className="console-header">
      <div className="console-header__brand">
        <Wordmark />
        <span className="console-header__label">Impiricus view</span>
      </div>
      <div className="console-header__status">
        {reconnecting && <span className="console-header__reconnecting">reconnecting…</span>}
        <span className={`backend-indicator backend-indicator--${backend}`} role="status">
          <span className="backend-indicator__dot" aria-hidden="true" />
          {BACKEND_TEXT[backend]}
        </span>
      </div>
    </header>
  );
}
