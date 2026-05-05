import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header.jsx";
import NavBar from "./components/NavBar.jsx";
import SearchBar from "./components/SearchBar.jsx";
import TierSection from "./components/TierSection.jsx";
import WeaponCard from "./components/WeaponCard.jsx";

const TIERS = ["Absolute Meta", "Meta", "A", "B", "F"];
const PLAY_STYLES = ["All", "Long Range", "Close Range", "Sniper", "Support", "Hip Fire", "Aggressive", "Lowest Recoil"];
const API = import.meta.env.VITE_API_URL ?? "";

const MOCK_BUILDS = [
  {
    id: 1, weapon_name: "Voyak KT-3", weapon_class: "AR", game: "Warzone", play_style: "Long Range", tier: "Absolute Meta",
    attachments: ["Optic: Fang Hoverpoint ELO", "Muzzle: Monolithic Suppressor", "Barrel: 17.6\" LTI Grav-4 Barrel", "Magazine: SK-Garrison Drum", "Stock: V-Last Control Pad"],
    reasoning: "Season 3 top AR. Dominates long-range with unmatched recoil control and velocity.", confidence: 0.97,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 2, weapon_name: "VST", weapon_class: "SMG", game: "Warzone", play_style: "Close Range", tier: "Absolute Meta",
    attachments: ["Muzzle: Hawker Series 45", "Barrel: 14\" LTI Expedition Barrel", "Magazine: Avarice Extended Mag II", "Stock: Hawker Cub-55 Pad", "Fire Mods: Buffer Springs"],
    reasoning: "Best close-range SMG in the game. Fastest TTK under 15m.", confidence: 0.96,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 3, weapon_name: "Strider 300", weapon_class: "Sniper", game: "Warzone", play_style: "Sniper", tier: "Absolute Meta",
    attachments: ["Muzzle: Monolithic Suppressor", "Barrel: 25\" Bowen Grooved Barrel", "Underbarrel: Cornerstone-642 Guard", "Rear Grip: Hatch Quick Grip", "Fire Mods: .300 WM Overpressured"],
    reasoning: "The dominant sniper. One-shot potential at all ranges.", confidence: 0.95,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 4, weapon_name: "MK.78", weapon_class: "LMG", game: "Warzone", play_style: "Long Range", tier: "Meta",
    attachments: ["Optic: Greaves Accuspot 3X", "Muzzle: RL-7.62 Compensator", "Barrel: 25\" EAM Heavy Barrel", "Underbarrel: Bowen Sentry Foregrip", "Fire Mods: Accelerated Recoil System"],
    reasoning: "Highest pick-rate weapon. Insane damage at range with forgiving recoil.", confidence: 0.92,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 5, weapon_name: "Dravec 45", weapon_class: "SMG", game: "Warzone", play_style: "Close Range", tier: "Meta",
    attachments: ["Muzzle: Hawker Series 45", "Barrel: 19\" EAM Horizon Barrel", "Magazine: Gator Extended Mag", "Laser: MFS Agile Laser Pro", "Fire Mods: Bolt Carrier Group"],
    reasoning: "Excellent all-rounder SMG. Easy to use for any skill level.", confidence: 0.88,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 6, weapon_name: "SG-12", weapon_class: "Shotgun", game: "Warzone", play_style: "Close Range", tier: "A",
    attachments: ["Muzzle: Breacher Onyx Brake", "Barrel: 20\" Hawker Reach Barrel", "Underbarrel: Redwell Dash Handstop", "Magazine: Bowen Bighorn Drum", "Laser: Convergence Box Laser"],
    reasoning: "Best shotgun in the meta. Dangerous within 5m.", confidence: 0.77,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
  {
    id: 7, weapon_name: "RAM-7", weapon_class: "AR", game: "Warzone", play_style: "Long Range", tier: "B",
    attachments: ["Muzzle: Casus Brake", "Barrel: Cronen Headwind Long Barrel", "Underbarrel: Bruen Heavy Support Grip", "Magazine: 60 Round Drum", "Stock: HVS 3.4 Pad"],
    reasoning: "Legacy MW3 AR. Outclassed by every BO7 AR. Skip it.", confidence: 0.58,
    source_type: "website", source_url: "https://wzhub.gg/loadouts", source_title: "wzhub.gg - Warzone Meta",
  },
];

function groupByTier(builds) {
  return TIERS.reduce((acc, tier) => {
    acc[tier] = builds.filter((b) => b.tier === tier);
    return acc;
  }, {});
}

export default function App() {
  const [builds, setBuilds] = useState([]);
  const [stats, setStats] = useState(null);
  const [styleFilter, setStyleFilter] = useState("All");
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
      setBuilds(MOCK_BUILDS);
      setStats({ total: MOCK_BUILDS.length, by_tier: {}, last_scraped: null });
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const afterStyle = styleFilter === "All"
    ? builds
    : builds.filter((b) => b.play_style === styleFilter);

  const query = search.trim().toLowerCase();
  const filtered = query
    ? afterStyle.filter((b) => b.weapon_name.toLowerCase().includes(query))
    : afterStyle;

  const grouped = groupByTier(filtered);
  const isSearching = query.length > 0;

  return (
    <div style={styles.app}>
      <Header stats={stats} />
      <NavBar />

      {usingMock && (
        <div style={styles.mockBanner}>
          ⚠ Showing sample data — start the backend or trigger Refresh from Admin
        </div>
      )}

      <div style={styles.controls}>
        <div style={styles.styleFilters}>
          {PLAY_STYLES.map((s) => (
            <button
              key={s}
              style={{ ...styles.chip, ...(styleFilter === s ? styles.chipActive : {}) }}
              onClick={() => setStyleFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <SearchBar value={search} onChange={setSearch} />
      </div>

      <main style={styles.main}>
        {loading ? (
          <div style={styles.loading}>Loading builds…</div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>
            {isSearching ? `No weapons matching "${search}".` : "No builds found. Run the pipeline from the Admin page."}
          </div>
        ) : isSearching ? (
          <div style={styles.searchResults}>
            {filtered.map((b) => <WeaponCard key={b.id} build={b} />)}
          </div>
        ) : (
          TIERS.map((tier) =>
            grouped[tier]?.length ? (
              <TierSection key={tier} tier={tier} builds={grouped[tier]} />
            ) : null
          )
        )}
      </main>

      <footer style={styles.footer}>
        Built for the homies · data from wzhub.gg · classified by Claude
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
  controls: {
    maxWidth: 1100, margin: "0 auto", width: "100%",
    padding: "16px 24px 0",
    display: "flex", alignItems: "center", justifyContent: "space-between",
    flexWrap: "wrap", gap: 12,
  },
  styleFilters: { display: "flex", gap: 6, flexWrap: "wrap" },
  chip: {
    background: "#13131f", border: "1px solid #2a2a40", color: "#9090b0",
    borderRadius: 20, padding: "5px 14px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", transition: "all 0.15s",
  },
  chipActive: { background: "#1e1e3a", border: "1px solid #4fc3f7", color: "#4fc3f7" },
  main: {
    maxWidth: 1100, margin: "0 auto", padding: "16px 24px 48px",
    width: "100%", display: "flex", flexDirection: "column", gap: 20, flex: 1,
  },
  searchResults: { display: "flex", flexDirection: "column", gap: 12 },
  loading: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 16 },
  empty: { textAlign: "center", color: "#6b6b8a", padding: 60, fontSize: 15 },
  footer: {
    textAlign: "center", padding: "20px 24px", fontSize: 12,
    color: "#3a3a5a", borderTop: "1px solid #1a1a2e",
  },
};
