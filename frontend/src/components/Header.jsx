import { useState } from "react";

export default function Header({ stats, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);
  const [showPasswordInput, setShowPasswordInput] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleRefreshClick() {
    setShowPasswordInput(true);
    setPassword("");
    setError("");
  }

  async function handleSubmitPassword() {
    if (!password) return;
    setRefreshing(true);
    setShowPasswordInput(false);
    setError("");
    try {
      const api = import.meta.env.VITE_API_URL ?? "";
      const res = await fetch(`${api}/api/pipeline/run`, {
        method: "POST",
        headers: { "x-pipeline-secret": password },
      });
      if (res.status === 401) {
        setError("Wrong password.");
        setRefreshing(false);
        return;
      }
      setTimeout(() => {
        onRefresh();
        setRefreshing(false);
      }, 60_000);
    } catch {
      setRefreshing(false);
    }
    setPassword("");
  }

  function handleCancel() {
    setShowPasswordInput(false);
    setPassword("");
    setError("");
  }

  const lastUpdated = stats?.last_scraped
    ? new Date(stats.last_scraped + "Z").toLocaleString()
    : "Never";

  const nextScrape = stats?.next_scrape
    ? new Date(stats.next_scrape).toLocaleString()
    : null;

  return (
    <header style={styles.header}>
      <div style={styles.inner}>
        <div style={styles.brand}>
          <span style={styles.logo}>⚔</span>
          <div>
            <h1 style={styles.title}>WARZONE META</h1>
            <p style={styles.subtitle}>Community-ranked weapon builds · powered by AI</p>
          </div>
        </div>

        <div style={styles.right}>
          {stats && (
            <div style={styles.statPill}>
              <span style={styles.statNum}>{stats.total}</span>
              <span style={styles.statLabel}>builds tracked</span>
            </div>
          )}
          <div style={styles.lastUpdated}>
            <div>Last updated: {lastUpdated}</div>
            {nextScrape && <div style={styles.nextScrape}>Next scrape: {nextScrape}</div>}
          </div>

          {showPasswordInput ? (
            <div style={styles.passwordRow}>
              <input
                style={styles.passwordInput}
                type="password"
                placeholder="Enter password…"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmitPassword()}
                autoFocus
              />
              <button style={styles.confirmBtn} onClick={handleSubmitPassword}>Go</button>
              <button style={styles.cancelBtn} onClick={handleCancel}>✕</button>
              {error && <span style={styles.errorMsg}>{error}</span>}
            </div>
          ) : (
            <button
              style={{ ...styles.refreshBtn, opacity: refreshing ? 0.6 : 1 }}
              onClick={handleRefreshClick}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing…" : "↻ Refresh"}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

const styles = {
  header: {
    background: "linear-gradient(180deg, #0d0d20 0%, #0d0d14 100%)",
    borderBottom: "1px solid #2a2a40",
    padding: "20px 24px",
    position: "sticky",
    top: 0,
    zIndex: 100,
    backdropFilter: "blur(12px)",
  },
  inner: {
    maxWidth: 1100,
    margin: "0 auto",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 14,
  },
  logo: {
    fontSize: 32,
    lineHeight: 1,
  },
  title: {
    fontFamily: "Rajdhani, sans-serif",
    fontSize: 28,
    fontWeight: 700,
    letterSpacing: "0.08em",
    color: "#fff",
    lineHeight: 1,
  },
  subtitle: {
    fontSize: 12,
    color: "#6b6b8a",
    marginTop: 2,
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    flexWrap: "wrap",
  },
  statPill: {
    background: "#1a1a2e",
    border: "1px solid #2a2a40",
    borderRadius: 20,
    padding: "4px 14px",
    display: "flex",
    alignItems: "baseline",
    gap: 6,
  },
  statNum: {
    fontSize: 18,
    fontWeight: 700,
    color: "#fff",
    fontFamily: "Rajdhani, sans-serif",
  },
  statLabel: {
    fontSize: 11,
    color: "#6b6b8a",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  lastUpdated: {
    fontSize: 12,
    color: "#6b6b8a",
    lineHeight: 1.6,
  },
  nextScrape: {
    fontSize: 11,
    color: "#4a4a6a",
  },
  refreshBtn: {
    background: "transparent",
    border: "1px solid #2a2a40",
    color: "#e8e8f0",
    borderRadius: 8,
    padding: "7px 16px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "border-color 0.2s, background 0.2s",
  },
  passwordRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  passwordInput: {
    background: "#1a1a2e",
    border: "1px solid #3a3a5a",
    borderRadius: 8,
    color: "#e8e8f0",
    padding: "6px 12px",
    fontSize: 13,
    outline: "none",
    width: 150,
  },
  confirmBtn: {
    background: "#3a3a8a",
    border: "none",
    color: "#fff",
    borderRadius: 8,
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  cancelBtn: {
    background: "transparent",
    border: "1px solid #2a2a40",
    color: "#6b6b8a",
    borderRadius: 8,
    padding: "6px 10px",
    fontSize: 13,
    cursor: "pointer",
  },
  errorMsg: {
    fontSize: 12,
    color: "#ff6b6b",
  },
};
