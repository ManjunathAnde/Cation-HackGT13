import { useState } from "react";
import { api } from "../../api.js";
import SecondaryButton from "../ui/SecondaryButton.jsx";

// The §12 demo doctor, exactly as onboarded in the demo path.
const DEMO_DOCTOR = {
  id: "dr_patel",
  name: "Dr. Patel",
  specialty: "endocrinology",
  conditions: ["type 2 diabetes", "chronic kidney disease"],
  interests: ["ozempic safety"],
  frequency: "weekly",
};

// note ({ ok, text } or null) is kept by the page, so it survives the switch from the
// "not onboarded" view to the full console after a successful reset.
export default function ResetDemo({ note, onResult }) {
  const [busy, setBusy] = useState(false);

  async function reset() {
    if (!window.confirm("This clears Dr. Patel's thread, vault, and scores.")) return;
    setBusy(true);
    const result = await api("POST", "/onboard", DEMO_DOCTOR);
    setBusy(false);
    if (result.ok) onResult({ ok: true, text: "Dr. Patel reset." });
    else if (result.status === 0) onResult({ ok: false, text: "Can't reach Cation. Is the backend running?" });
    else onResult({ ok: false, text: result.data.detail });
  }

  return (
    <div className="reset-demo">
      <SecondaryButton type="button" onClick={reset} disabled={busy}>
        {busy ? "Resetting…" : "Reset demo"}
      </SecondaryButton>
      {note && <p className={`console-note console-note--${note.ok ? "ok" : "error"}`}>{note.text}</p>}
    </div>
  );
}
