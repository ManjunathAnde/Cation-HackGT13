import { useState } from "react";
import Panel from "../ui/Panel.jsx";
import SecondaryButton from "../ui/SecondaryButton.jsx";
import SegmentedControl from "../ui/SegmentedControl.jsx";
import TextInput from "../ui/TextInput.jsx";
import { OTHER, PRESET_DOCTORS } from "./doctors.js";

const OPTIONS = [
  ...PRESET_DOCTORS.map((doctor) => ({ value: doctor.id, label: doctor.name, caption: doctor.id })),
  { value: OTHER, label: "Other ID", caption: "Watch any doctor ID" },
];

// mode: a preset id or OTHER; onMode(mode). onWatch(id) applies a typed ID (on Watch or Enter only,
// so the console never polls half-typed IDs).
export default function DoctorSwitcher({ mode, watchedId, onMode, onWatch }) {
  const [draft, setDraft] = useState(watchedId || "");

  function watch(event) {
    event.preventDefault();
    if (draft.trim()) onWatch(draft.trim());
  }

  return (
    <Panel className="doctor-switcher" aria-label="Doctor">
      <h2 className="console-panel-title">Doctor</h2>
      <SegmentedControl label="Doctor" options={OPTIONS} value={mode} onChange={onMode} />
      {mode === OTHER && (
        <form className="doctor-switcher__other" onSubmit={watch}>
          <TextInput
            id="console-other-id"
            type="text"
            placeholder="e.g. dr_maya_chen"
            aria-label="Doctor ID"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <SecondaryButton type="submit">Watch</SecondaryButton>
        </form>
      )}
    </Panel>
  );
}
