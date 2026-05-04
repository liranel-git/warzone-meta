import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "";

export default function AdminPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState(null); // null | "running" | "success" | "error"
  const [errorMsg, setErrorMsg] = useState("");

  async function handleRefresh() {
    if (!password) return;
    setStatus("running");
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/pipeline/run`, {
        method: "POST",
        headers: { "x-pipeline-secret": password },
      });
      if (res.status === 401) {
        setErrorMsg("Wrong password.");
        setStatus("error");
        return;
      }
      setStatus("success");
    } catch {
      setErrorMsg("Could not reach the server.");
      setStatus("error");
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <button style={styles.back} onClick={() => navigate("/")}>← Back</button>
        <h2 style={styles.title}>Admin Panel</h2>
        <p style={styles.desc}>
          Trigger the scraper pipeline to pull the latest YouTube videos and re-classify weapon builds.
        </p>

        <label style={styles.label}>Admin password</label>
        <input
          style={styles.input}
          type="password"
          placeholder="Enter password…"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleRefresh()}
          disabled={status === "running"}
        />

        <button
          style={{
            ...styles.btn,
            opacity: status === "running" || !password ? 0.6 : 1,
          }}
          onClick={handleRefresh}
          disabled={status === "running" || !password}
        >
          {status === "running" ? "Pipeline running…" : "↻ Refresh Data"}
        </button>

        {status === "success" && (
          <p style={styles.success}>
            Pipeline started. Data will update in ~60 seconds.{" "}
            <span style={styles.link} onClick={() => navigate("/")}>Go back →</span>
          </p>
        )}
        {status === "error" && <p style={styles.error}>{errorMsg}</p>}
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#0d0d14",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    background: "#12121e",
    border: "1px solid #2a2a40",
    borderRadius: 16,
    padding: "40px 48px",
    width: "100%",
    maxWidth: 420,
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  back: {
    background: "none",
    border: "none",
    color: "#6b6b8a",
    fontSize: 13,
    cursor: "pointer",
    textAlign: "left",
    padding: 0,
    marginBottom: 8,
  },
  title: {
    fontFamily: "Rajdhani, sans-serif",
    fontSize: 26,
    fontWeight: 700,
    color: "#fff",
    margin: 0,
  },
  desc: {
    fontSize: 13,
    color: "#6b6b8a",
    lineHeight: 1.6,
    margin: 0,
  },
  label: {
    fontSize: 12,
    color: "#8888aa",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  input: {
    background: "#1a1a2e",
    border: "1px solid #3a3a5a",
    borderRadius: 8,
    color: "#e8e8f0",
    padding: "10px 14px",
    fontSize: 14,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  },
  btn: {
    background: "#3a3a8a",
    border: "none",
    color: "#fff",
    borderRadius: 10,
    padding: "12px 0",
    fontSize: 15,
    fontWeight: 700,
    cursor: "pointer",
    letterSpacing: "0.04em",
  },
  success: {
    fontSize: 13,
    color: "#6bffb8",
    margin: 0,
  },
  error: {
    fontSize: 13,
    color: "#ff6b6b",
    margin: 0,
  },
  link: {
    cursor: "pointer",
    textDecoration: "underline",
  },
};
