import { useEffect, useRef, useState } from "react";
import Panel from "../ui/Panel.jsx";

// ion: { pick, why } from GET /profile (null until loaded).
export default function IonPanel({ ion }) {
  const pick = ion ? ion.pick : null;
  const previous = useRef(null);
  const [changes, setChanges] = useState(0);

  useEffect(() => {
    if (pick === null) return;
    if (previous.current !== null && previous.current !== pick) setChanges((n) => n + 1);
    previous.current = pick;
  }, [pick]);

  // Keyed on the change count so the highlight animation replays on every new pick.
  return (
    <Panel
      key={changes}
      className={changes > 0 ? "ion-panel ion-panel--changed" : "ion-panel"}
      aria-label="ION (simulated)"
    >
      <p className="ion-panel__label">ION (simulated)</p>
      <p className="ion-panel__pick">{ion ? ion.pick : "…"}</p>
      <p className="ion-panel__why">{ion ? ion.why : ""}</p>
    </Panel>
  );
}
