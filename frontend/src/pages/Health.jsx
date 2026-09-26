import { useEffect, useState } from "react";
import { api } from "../api.js";

// Checkpoint 2 health check, kept on "/".
export default function Health() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    api("GET", "/health").then((result) => setStatus(result.ok && result.data.ok ? "connected" : "down"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Cation</h1>
      <p>
        {status === "checking" && "checking backend…"}
        {status === "connected" && "backend connected ✓"}
        {status === "down" && "backend not running"}
      </p>
    </main>
  );
}
