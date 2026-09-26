import { useState } from "react";
import { api, APPROVED_TOPICS, DOCTOR_ID } from "../api.js";
import { navigate } from "../router.jsx";
import ConditionTypeahead from "../components/ConditionTypeahead.jsx";
import CheckPill from "../components/ui/CheckPill.jsx";
import FieldError from "../components/ui/FieldError.jsx";
import FieldLabel from "../components/ui/FieldLabel.jsx";
import Notice from "../components/ui/Notice.jsx";
import PhoneColumn from "../components/ui/PhoneColumn.jsx";
import PrimaryButton from "../components/ui/PrimaryButton.jsx";
import SegmentedControl from "../components/ui/SegmentedControl.jsx";
import TextInput from "../components/ui/TextInput.jsx";
import Wordmark from "../components/ui/Wordmark.jsx";
import "./onboard.css";

const FREQUENCIES = [
  { value: "weekly", label: "Weekly", caption: "About one update a week" },
  { value: "daily", label: "Daily", caption: "About one update a day" },
];
const UNREACHABLE = "Can't reach Cation. Is the backend running?";

const titleCase = (topic) => topic.replace(/(^|[\s-])\w/g, (letter) => letter.toUpperCase());

// Checks the form only; every product decision is made by the backend.
function validate({ name, specialty, conditions, interests }) {
  const errors = {};
  if (!name.trim()) errors.name = "Enter your name.";
  if (!specialty.trim()) errors.specialty = "Enter your specialty.";
  if (conditions.length === 0 && interests.length === 0) errors.topics = "Add at least one condition or interest.";
  return errors;
}

export default function Onboard() {
  const [name, setName] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [conditions, setConditions] = useState([]);
  const [interests, setInterests] = useState([]);
  const [frequency, setFrequency] = useState("weekly");
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const clearError = (field) => setErrors((current) => ({ ...current, [field]: undefined }));

  function toggleInterest(topic, checked) {
    setInterests((current) => (checked ? [...current, topic] : current.filter((t) => t !== topic)));
    clearError("topics");
  }

  async function onSubmit(event) {
    event.preventDefault();
    const found = validate({ name, specialty, conditions, interests });
    setErrors(found);
    setNotice("");
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    const result = await api("POST", "/onboard", {
      id: DOCTOR_ID,
      name: name.trim(),
      specialty: specialty.trim(),
      conditions,
      interests,
      frequency,
    });
    setSubmitting(false);
    if (result.ok) navigate("/phone/brief");
    else setNotice(result.status === 0 ? UNREACHABLE : result.data.detail);
  }

  return (
    <PhoneColumn>
      <Wordmark />
      <p className="onboard__eyebrow">Personal research brief</p>
      <h1 className="onboard__title">Stay current without chasing every paper.</h1>
      <p className="onboard__subtitle">
        Tell us what matters in your practice. We'll send one focused update at a time.
      </p>

      <form className="onboard__form" onSubmit={onSubmit} noValidate>
        <div className="onboard__group">
          <FieldLabel htmlFor="onboard-name" text="Name" meta="Required" />
          <TextInput
            id="onboard-name"
            type="text"
            autoComplete="name"
            placeholder="Dr. Patel"
            value={name}
            invalid={Boolean(errors.name)}
            aria-describedby="onboard-name-error"
            onChange={(event) => {
              setName(event.target.value);
              clearError("name");
            }}
          />
          <FieldError id="onboard-name-error">{errors.name}</FieldError>
        </div>

        <div className="onboard__group">
          <FieldLabel htmlFor="onboard-specialty" text="Specialty" meta="Required" />
          <TextInput
            id="onboard-specialty"
            type="text"
            placeholder="e.g. Endocrinology"
            value={specialty}
            invalid={Boolean(errors.specialty)}
            aria-describedby="onboard-specialty-error"
            onChange={(event) => {
              setSpecialty(event.target.value);
              clearError("specialty");
            }}
          />
          <FieldError id="onboard-specialty-error">{errors.specialty}</FieldError>
        </div>

        <div className="onboard__group">
          <FieldLabel
            htmlFor="onboard-conditions"
            text="Conditions in your practice"
            meta="Add at least one condition or interest"
          />
          <ConditionTypeahead
            inputId="onboard-conditions"
            selected={conditions}
            invalid={Boolean(errors.topics)}
            describedBy="onboard-conditions-help onboard-topics-error"
            onChange={(next) => {
              setConditions(next);
              clearError("topics");
            }}
          />
          <p className="onboard__helper" id="onboard-conditions-help">
            Practice-level only — no patient details.
          </p>
          <FieldError id="onboard-topics-error">{errors.topics}</FieldError>
        </div>

        <fieldset className="onboard__group onboard__fieldset">
          <legend className="onboard__legend">
            <FieldLabel text="Interests" meta="Select any" />
          </legend>
          <div className="onboard__pills">
            {APPROVED_TOPICS.map((topic) => (
              <CheckPill
                key={topic}
                label={titleCase(topic)}
                checked={interests.includes(topic)}
                onChange={(checked) => toggleInterest(topic, checked)}
              />
            ))}
          </div>
        </fieldset>

        <div className="onboard__group">
          <FieldLabel text="Frequency" />
          <SegmentedControl label="Frequency" options={FREQUENCIES} value={frequency} onChange={setFrequency} />
        </div>

        <Notice>{notice}</Notice>
        <PrimaryButton type="submit" disabled={submitting}>
          {submitting ? "Starting…" : "Start my research brief →"}
        </PrimaryButton>
        <p className="onboard__caption">About 2 minutes a week. Adjust your topics anytime.</p>
      </form>
    </PhoneColumn>
  );
}
