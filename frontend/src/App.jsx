import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.ok ? "connected" : "down"))
      .catch(() => setStatus("down"));
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
