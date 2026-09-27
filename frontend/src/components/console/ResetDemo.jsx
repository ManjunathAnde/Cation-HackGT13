import { useState } from "react";
import { api } from "../../api.js";
import SecondaryButton from "../ui/SecondaryButton.jsx";

// doctor: a preset from doctors.js, onboarded again with its fixed profile.
// note ({ ok, text } or null) is kept by the doctor's console, so it survives the switch from the
// "not onboarded" view to the full console after a successful reset.
export default function ResetDemo({ doctor, note, onResult }) {
  const [busy, setBusy] = useState(false);

  async function reset() {
    if (!window.confirm(`This clears ${doctor.name}'s thread, vault, and scores.`)) return;
    setBusy(true);
    const result = await api("POST", "/onboard", doctor);
    setBusy(false);
    if (result.ok) onResult({ ok: true, text: `${doctor.name} reset.` });
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
