// GET /specialties: loaded once per page load and shared. The backend owns the lists.
import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

let request = null; // the one in-flight or finished request, reused by every caller

function loadSpecialties() {
  if (!request) {
    request = api("GET", "/specialties").then((result) => {
      if (!result.ok) request = null; // allow Retry after a failure
      return result;
    });
  }
  return request;
}

// { status: "loading" | "ready" | "error", specialties, retry }
export function useSpecialties() {
  const [state, setState] = useState({ status: "loading", specialties: [] });

  const load = useCallback(() => {
    setState({ status: "loading", specialties: [] });
    let live = true;
    loadSpecialties().then((result) => {
      if (live) setState(result.ok ? { status: "ready", specialties: result.data } : { status: "error", specialties: [] });
    });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => load(), [load]);
  return { ...state, retry: load };
}

// Topic value → display label from every specialty; empty until loaded (callers fall back to formatting).
export function useTopicLabels() {
  const { specialties } = useSpecialties();
  const labels = {};
  for (const specialty of specialties) {
    for (const topic of specialty.topics) labels[topic.value] = topic.label;
  }
  return labels;
}
