import { useState } from "react";

export default function Header({ stats, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const api = import.meta.env.VITE_API_URL ?? "";
      await fetch(`${api}/api/pipeline/run`, { method: "POST" });
      // Poll until last_scraped changes (simple approach: just reload after 60s)
      setTimeout(() => {
        onRefresh();
        setRefreshing(false);
      }, 60_000);
    } catch {
      setRefreshing(false);
    }
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
          <button
            style={{ ...styles.refreshBtn, opacity: refreshing ? 0.6 : 1 }}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing…" : "↻ Refresh"}
          </button>
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
    transition: "border-color 0.2s, background 0.2s",
  },
};
