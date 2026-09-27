// Backend access. The frontend makes no decisions: it sends user actions and shows results.

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The doctor shown when a /phone/* URL has no ?doctor= parameter.
export const DEFAULT_DOCTOR_ID = "dr_patel";

// Never throws. Returns { ok, status, data }; a network failure has status 0.
export async function api(method, path, body) {
  try {
    const response = await fetch(API_URL + path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 0, data: { detail: "Backend not reachable" } };
  }
}
