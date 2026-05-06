import { useState, useEffect, useCallback, useMemo } from "react";
import Header from "./components/Header.jsx";
import NavBar from "./components/NavBar.jsx";
import SearchBar from "./components/SearchBar.jsx";
import TierSection from "./components/TierSection.jsx";
import WeaponCard from "./components/WeaponCard.jsx";

const TIERS = ["Absolute Meta", "Meta", "A", "B", "F"];
const PLAY_STYLES = [
  "All",
  "Fast Movement",
  "Legacy Meta",
  "Rank Play",
  "Personal Meta Builds",
  "Casual and Meta",
  "Casual",
  "Team Play",
  "Meta and Follower Builds",
  "Codmunity",
  "WZ Meta",
  "WZ Hub",
];
const WEAPON_DOMINANCIES = [
  "Long Range",
  "Close Range",
  "Sniper",
  "Support",
  "Hip Fire",
  "Aggressive",
  "Lowest Recoil",
];
const API = import.meta.env.VITE_API_URL ?? "";

function groupByTier(builds) {
  return TIERS.reduce((acc, tier) => {
    acc[tier] = builds.filter((b) => b.tier === tier);
    return acc;
  }, {});
}

export default function App() {
  const [builds, setBuilds] = useState([]);
  const [stats, setStats] = useState(null);
  const [playStyle, setPlayStyle] = useState("All");
  const [dominancies, setDominancies] = useState([]); // empty = all
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [buildsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/builds?game=Warzone`),
        fetch(`${API}/api/stats`),
      ]);
      if (!buildsRes.ok) throw new Error("API unavailable");
      const buildsJson = await buildsRes.json();
      const statsJson = await statsRes.json();
      setBuilds(buildsJson.builds);
      setStats(statsJson);
      setUsingMock(false);
    } catch {
      setBuilds([]);
      setStats({ total: 0, by_tier: {}, last_scraped: null });
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // When play style changes, reset weapon dominancy selection.
  const onPlayStyleChange = (next) => {
    setPlayStyle(next);
    setDominancies([]);
  };

  const toggleDominancy = (d) => {
    setDominancies((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  };

  // Apply filters
  const afterPlayStyle = useMemo(() => (
    playStyle === "All" ? builds : builds.filter((b) => b.play_style === playStyle)
  ), [builds, playStyle]);

  const afterDominancy = useMemo(() => (
    dominancies.length === 0
      ? afterPlayStyle
      : afterPlayStyle.filter((b) => dominancies.includes(b.weapon_dominancy))
  ), [afterPlayStyle, dominancies]);

  const query = search.trim().toLowerCase();
  const filtered = query
    ? afterDominancy.filter((b) => b.weapon_name.toLowerCase().includes(query))
    : afterDominancy;

  // For "Search across all play styles" link — what would be found if we removed
  // the play style filter (but kept dominancy + search).
  const crossPlayStyleResults = useMemo(() => {
    if (!query) return [];
    const base = dominancies.length === 0
      ? builds
      : builds.filter((b) => dominancies.includes(b.weapon_dominancy));
    return base.filter((b) => b.weapon_name.toLowerCase().includes(query));
  }, [builds, dominancies, query]);

  const showCrossLink = query.length > 0
    && playStyle !== "All"
    && crossPlayStyleResults.length > filtered.length;

  const grouped = groupByTier(filtered);
  const isSearching = query.length > 0;

  return (
    <div style={styles.app}>
      <Header stats={stats} />
      <NavBar />

      {usingMock && (
        <div style={styles.mockBanner}>
          ⚠ Backend unreachable — start the backend or trigger Refresh from Admin
        </div>
      )}

      {/* Play style row */}
      <div style={styles.playStyleRow}>
        <div style={styles.psWrap}>
          {PLAY_STYLES.map((s) => (
            <button
              key={s}
              style={{ ...styles.psChip, ...(playStyle === s ? styles.psChipActive : {}) }}
              onClick={() => onPlayStyleChange(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Weapon dominancy row */}
      <div style={styles.controls}>
        <div style={styles.dominancyRow}>
          <span style={styles.dominancyLabel}>Weapon dominancy:</span>
          <button
            style={{ ...styles.tag, ...(dominancies.length === 0 ? styles.tagActive : {}) }}
            onClick={() => setDominancies([])}
          >
            All
          </button>
          {WEAPON_DOMINANCIES.map((d) => {
            const active = dominancies.includes(d);
            return (
              <button
                key={d}
                style={{ ...styles.tag, ...(active ? styles.tagActive : {}) }}
                onClick={() => toggleDominancy(d)}
              >
                {active && <span style={{ marginRight: 4 }}>✓</span>}
                {d}
              </button>
            );
          })}
        </div>
        <SearchBar value={search} onChange={setSearch} />
      </div>

      <main style={styles.main}>
        {loading ? (
          <div style={styles.loading}>Loading builds…</div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>
            {isSearching
              ? `No "${search}" matches in ${playStyle === "All" ? "any play style" : playStyle}.`
              : "No builds yet. Run the pipeline from Admin."}
            {showCrossLink && (
              <div style={{ marginTop: 16 }}>
                <button style={styles.crossLink} onClick={() => onPlayStyleChange("All")}>
                  Search "{search}" across all play styles →
                </button>
              </div>
            )}
          </div>
        ) : isSearching ? (
          <>
            <div style={styles.searchResults}>
              {filtered.map((b) => <WeaponCard key={b.id} build={b} />)}
            </div>
            {showCrossLink && (
              <div style={styles.crossLinkRow}>
                <button style={styles.crossLink} onClick={() => onPlayStyleChange("All")}>
                  Search "{search}" across all play styles → ({crossPlayStyleResults.length} more)
                </button>
              </div>
            )}
          </>
        ) : (
          TIERS.map((tier) =>
            grouped[tier]?.length ? (
              <TierSection key={tier} tier={tier} builds={grouped[tier]} />
            ) : null
          )
        )}
      </main>

      <footer style={styles.footer}>
        Built for the homies · classified by Claude
      </footer>
    </div>
  );
}

const styles = {
  app: { minHeight: "100vh", display: "flex", flexDirection: "column" },
  mockBanner: {
    background: "#1a1200", border: "1px solid #5a4000",
    color: "#ffb74d", fontSize: 13, padding: "10px 24px", textAlign: "center",
  },
  playStyleRow: {
    background: "#0d0d18",
    borderBottom: "1px solid #1a1a2e",
    padding: "12px 24px",
  },
  psWrap: {
    maxWidth: 1100, margin: "0 auto",
    display: "flex", gap: 6, flexWrap: "wrap",
  },
  psChip: {
    background: "#13131f", border: "1px solid #2a2a40", color: "#9090b0",
    borderRadius: 18, padding: "6px 14px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", transition: "all 0.15s",
    fontFamily: "Rajdhani, sans-serif", letterSpacing: "0.04em",
  },
  psChipActive: {
    background: "#1e1e3a", border: "1px solid #4fc3f7",
    color: "#4fc3f7",
  },
  controls: {
    maxWidth: 1100, margin: "0 auto", width: "100%",
    padding: "16px 24px 0",
    display: "flex", alignItems: "flex-start", justifyContent: "space-between",
    flexWrap: "wrap", gap: 12,
  },
  dominancyRow: { display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", flex: 1 },
  dominancyLabel: {
    fontSize: 11, color: "#6b6b8a", fontWeight: 700,
    letterSpacing: "0.06em", textTransform: "uppercase", marginRight: 4,
  },
  tag: {
    background: "#13131f", border: "1px solid #2a2a40", color: "#9090b0",
    borderRadius: 6, padding: "5px 12px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", transition: "all 0.15s",
  },
  tagActive: { background: "#1e1e3a", border: "1px solid #4fc3f7", color: "#4fc3f7" },
  main: {
    maxWidth: 1100, margin: "0 auto", padding: "16px 24px 48px",
    width: "100%", display: "flex", flexDirection: "column", gap: 20, flex: 1,
  },
  searchResults: { display: "flex", flexDirection: "column", gap: 12 },
  loading: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 16 },
  empty: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 15 },
  crossLinkRow: {
    textAlign: "center", padding: "20px 0 0",
    borderTop: "1px dashed #1a1a2e", marginTop: 12,
  },
  crossLink: {
    background: "none", border: "none", color: "#4fc3f7", cursor: "pointer",
    fontSize: 13, fontWeight: 600, textDecoration: "underline",
  },
  footer: {
    textAlign: "center", padding: "20px 24px", fontSize: 12,
    color: "#3a3a5a", borderTop: "1px solid #1a1a2e",
  },
};
