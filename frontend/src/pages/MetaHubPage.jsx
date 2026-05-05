import { useState } from "react";
import NavBar from "../components/NavBar.jsx";
import Header from "../components/Header.jsx";
import WeaponCard from "../components/WeaponCard.jsx";

const GAME_TABS = ["Warzone", "BO7", "BO6", "MW3", "MW2"];

const API = import.meta.env.VITE_API_URL ?? "";

import { useEffect } from "react";

export default function MetaHubPage() {
  const [activeGame, setActiveGame] = useState("Warzone");
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/builds?game=${encodeURIComponent(activeGame)}`)
      .then((r) => r.json())
      .then((d) => { setBuilds(d.builds ?? []); setLoading(false); })
      .catch(() => { setBuilds([]); setLoading(false); });
  }, [activeGame]);

  const GAME_COLORS = { Warzone: "#ffd700", BO7: "#00e676", BO6: "#4fc3f7", MW3: "#ffb74d", MW2: "#6b6b8a" };

  return (
    <div style={styles.page}>
      <Header />
      <NavBar />
      <main style={styles.main}>
        <h2 style={styles.heading}>Meta Hub</h2>
        <p style={styles.sub}>Best builds across every active Call of Duty title.</p>

        <div style={styles.gameTabs}>
          {GAME_TABS.map((g) => {
            const active = activeGame === g;
            const color = GAME_COLORS[g];
            return (
              <button
                key={g}
                style={{
                  ...styles.gameTab,
                  ...(active ? { borderColor: color, color, background: "#1a1a2e" } : {}),
                }}
                onClick={() => setActiveGame(g)}
              >
                {g}
              </button>
            );
          })}
        </div>

        {loading ? (
          <div style={styles.loading}>Loading builds…</div>
        ) : builds.length === 0 ? (
          <div style={styles.empty}>
            No {activeGame} builds in the database yet.{" "}
            {activeGame !== "Warzone"
              ? "These builds will be added in a future update."
              : "Run the pipeline from the Admin page to populate data."}
          </div>
        ) : (
          <div style={styles.grid}>
            {builds.map((b) => <WeaponCard key={b.id} build={b} />)}
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#0d0d14" },
  main: { maxWidth: 1100, margin: "0 auto", padding: "32px 24px 64px" },
  heading: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 32, fontWeight: 700,
    color: "#fff", letterSpacing: "0.06em", margin: "0 0 8px",
  },
  sub: { fontSize: 13, color: "#6b6b8a", margin: "0 0 28px" },
  gameTabs: { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 32 },
  gameTab: {
    background: "#12121e", border: "1px solid #2a2a40",
    color: "#6b6b8a", borderRadius: 8, padding: "8px 22px",
    fontSize: 14, fontWeight: 700, cursor: "pointer",
    fontFamily: "Rajdhani, sans-serif", letterSpacing: "0.06em",
  },
  grid: { display: "flex", flexDirection: "column", gap: 12 },
  loading: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 16 },
  empty: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 14, lineHeight: 1.7 },
};
