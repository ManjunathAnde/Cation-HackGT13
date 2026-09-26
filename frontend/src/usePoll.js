import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// Polls GET `path` every `ms`. Skips a tick while a request is in flight, keeps the last data
// when the backend can't be reached, and ignores responses older than the newest one applied.
// refresh() requests right away (used after an action) even if a poll is in flight.
export default function usePoll(path, ms) {
  const [state, setState] = useState({ data: null, status: null, reconnecting: false });
  const inFlight = useRef(0);
  const sent = useRef(0);
  const applied = useRef(0);
  const mounted = useRef(true);

  const request = useCallback(
    async (force) => {
      if (inFlight.current > 0 && !force) return;
      const id = ++sent.current;
      inFlight.current += 1;
      const result = await api("GET", path);
      inFlight.current -= 1;
      if (!mounted.current || id < applied.current) return;
      applied.current = id;
      setState((previous) => {
        if (result.status === 0) return { ...previous, reconnecting: true };
        return { data: result.ok ? result.data : null, status: result.status, reconnecting: false };
      });
    },
    [path]
  );

  useEffect(() => {
    mounted.current = true;
    request(false);
    const timer = setInterval(() => request(false), ms);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [request, ms]);

  const refresh = useCallback(() => request(true), [request]);
  return { ...state, refresh };
}
