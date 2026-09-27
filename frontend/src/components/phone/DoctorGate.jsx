import { useCallback, useEffect, useState } from "react";
import { api } from "../../api.js";
import { redirect, useDoctorId, withSearch } from "../../router.jsx";
import PhoneColumn from "../ui/PhoneColumn.jsx";
import PrimaryButton from "../ui/PrimaryButton.jsx";
import Wordmark from "../ui/Wordmark.jsx";

// Doctor-app gate: the page renders only once the URL's doctor (?doctor=, default Dr. Patel) exists.
// 404 → onboarding (keeping ?doctor=); backend unreachable → message with Retry.
export default function DoctorGate({ children }) {
  const doctorId = useDoctorId();
  const [state, setState] = useState("checking");

  const check = useCallback(async () => {
    setState("checking");
    const result = await api("GET", `/profile/${doctorId}`);
    if (result.ok) setState("ready");
    else if (result.status === 404) redirect(withSearch("/phone/onboard"));
    else setState("offline");
  }, [doctorId]);

  useEffect(() => {
    check();
  }, [check]);

  if (state === "ready") return children;
  return (
    <PhoneColumn>
      <Wordmark />
      {state === "offline" && (
        <div className="gate">
          <p className="gate__text">Can't reach Cation.</p>
          <PrimaryButton type="button" onClick={check}>
            Retry
          </PrimaryButton>
        </div>
      )}
    </PhoneColumn>
  );
}
