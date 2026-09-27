// Minimal pathname router: no router library (blueprint §13).
import { useEffect, useState } from "react";
import { DEFAULT_DOCTOR_ID } from "./api.js";

export function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

// Like navigate, but replaces the history entry so Back doesn't return to the redirecting path.
export function redirect(path) {
  window.history.replaceState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function currentLocation() {
  return { path: window.location.pathname, search: window.location.search };
}

// { path, search }, updated on every navigation (also when only the query string changes).
export function useLocation() {
  const [location, setLocation] = useState(currentLocation);
  useEffect(() => {
    const update = () => setLocation(currentLocation());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  return location;
}

export function usePath() {
  return useLocation().path;
}

// The doctor for /phone/* pages: ?doctor=<id>, else Dr. Patel.
export function useDoctorId() {
  const { search } = useLocation();
  return new URLSearchParams(search).get("doctor") || DEFAULT_DOCTOR_ID;
}

// `path` with the current query string kept (so ?doctor= survives navigation).
export function withSearch(path) {
  return path + window.location.search;
}
