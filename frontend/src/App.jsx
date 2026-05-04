import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header.jsx";
import FilterBar from "./components/FilterBar.jsx";
import TierSection from "./components/TierSection.jsx";

const TIERS = ["Absolute Meta", "Meta", "A", "B", "F"];
const API = import.meta.env.VITE_API_URL ?? "";

// Mock data shown when the API isn't running yet
const MOCK_BUILDS = [
  {
    id: 1, weapon_name: "MCW", weapon_class: "AR", tier: "Absolute Meta",
    attachments: ["Muzzle: Quartermaster", "Barrel: 16.5\" MCW Cyclone Long", "Stock: RB Regal Assault Stock", "Underbarrel: FTAC Ripper 56", "Magazine: 40 Round Mag"],
    reasoning: "Dominates mid-range with minimal recoil. The undisputed AR pick this season.", confidence: 0.95,
    source_type: "reddit", source_url: "https://reddit.com/r/CODWarzone", source_title: "MCW is actually broken right now",
  },
  {
    id: 2, weapon_name: "Holger 26", weapon_class: "LMG", tier: "Absolute Meta",
    attachments: ["Muzzle: VT-7 Spiritfire Suppressor", "Barrel: Holger Factory Barrel", "Stock: Holger Factory Stock", "Underbarrel: Bruen Heavy Support Grip", "Magazine: 100 Round Belt"],
    reasoning: "Best TTK in the game at range. The 100-round belt means you never run dry.", confidence: 0.92,
    source_type: "youtube", source_url: "https://youtube.com", source_title: "TOP 5 WARZONE WEAPONS 2025",
  },
  {
    id: 3, weapon_name: "Rival-9", weapon_class: "SMG", tier: "Meta",
    attachments: ["Muzzle: Shadowstrike Suppressor", "Barrel: Rival-C Clearshot Barrel", "Stock: Rival Factory Stock", "Rear Grip: Rival Vice Assault Grip", "Magazine: 50 Round Drum"],
    reasoning: "Best close-range option. Lightning fast TTK inside 15m.", confidence: 0.88,
    source_type: "reddit", source_url: "https://reddit.com/r/CODLoadouts", source_title: "Current SMG tier list",
  },
  {
    id: 4, weapon_name: "MTZ-762", weapon_class: "Marksman", tier: "Meta",
    attachments: ["Muzzle: VT-7 Spiritfire Suppressor", "Barrel: MTZ Clinch Pro Barrel", "Stock: MTZ Marauder Stock", "Underbarrel: FTAC Ripper 56", "Ammunition: 5.56 High Velocity"],
    reasoning: "One-shot headshot potential at any range. Cracked in the right hands.", confidence: 0.85,
    source_type: "youtube", source_url: "https://youtube.com", source_title: "Best marksman rifles Warzone",
  },
  {
    id: 5, weapon_name: "RAM-7", weapon_class: "AR", tier: "A",
    attachments: ["Muzzle: Quartermaster", "Barrel: Princeps Long Barrel", "Stock: RB Regal Assault Stock", "Underbarrel: FTAC Ripper 56", "Rear Grip: Sakin ZX Grip"],
    reasoning: "Consistent and reliable. Slightly lower ceiling than MCW but easier to control.", confidence: 0.78,
    source_type: "reddit", source_url: "https://reddit.com/r/CODWarzone", source_title: "RAM-7 hidden gem loadout",
  },
  {
    id: 6, weapon_name: "Kastov 762", weapon_class: "AR", tier: "B",
    attachments: ["Muzzle: Castellan-300 SR", "Barrel: KAS-10 584mm Barrel", "Stock: Kastov-74U Factory", "Underbarrel: FTAC Ripper 56", "Magazine: 40 Round Mag"],
    reasoning: "Was meta last season but nerfs hit hard. Still workable in the right hands.", confidence: 0.72,
    source_type: "reddit", source_url: "https://reddit.com/r/CODWarzone", source_title: "Is Kastov still good?",
  },
  {
    id: 7, weapon_name: "ISO 9mm", weapon_class: "SMG", tier: "F",
    attachments: ["Muzzle: Shadowstrike Suppressor", "Barrel: Fielder-T50 Barrel", "Stock: ISO Uproar Stock", "Rear Grip: ISO Sturdshot Rear Grip", "Magazine: 50 Round Drum"],
    reasoning: "Nerfed three times in a row. Every other SMG beats it. Don't run this.", confidence: 0.9,
    source_type: "reddit", source_url: "https://reddit.com/r/CODWarzone", source_title: "ISO 9mm after nerf is unplayable",
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
  const [classFilter, setClassFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [buildsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/builds`),
        fetch(`${API}/api/stats`),
      ]);
      if (!buildsRes.ok) throw new Error("API unavailable");
      const buildsJson = await buildsRes.json();
      const statsJson = await statsRes.json();
      setBuilds(buildsJson.builds);
      setStats(statsJson);
      setUsingMock(false);
    } catch {
      // API not running yet — show mock data so the UI is still useful
      setBuilds(MOCK_BUILDS);
      setStats({ total: MOCK_BUILDS.length, by_tier: {}, last_scraped: null });
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = classFilter === "All"
    ? builds
    : builds.filter((b) => b.weapon_class === classFilter);

  const grouped = groupByTier(filtered);

  return (
    <div style={styles.app}>
      <Header stats={stats} />

      {usingMock && (
        <div style={styles.mockBanner}>
          ⚠ Showing sample data — start the backend to load live builds
          (<code>cd warzone-meta\backend</code> then <code>uvicorn api:app --reload</code>)
        </div>
      )}

      <FilterBar selected={classFilter} onChange={setClassFilter} />

      <main style={styles.main}>
        {loading ? (
          <div style={styles.loading}>Loading builds…</div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>No builds found. Run the pipeline to scrape fresh data.</div>
        ) : (
          TIERS.map((tier) =>
            grouped[tier]?.length ? (
              <TierSection key={tier} tier={tier} builds={grouped[tier]} />
            ) : null
          )
        )}
      </main>

      <footer style={styles.footer}>
        Built for the homies · scraped from Reddit &amp; YouTube · classified by Claude
      </footer>
    </div>
  );
}

const styles = {
  app: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
  },
  mockBanner: {
    background: "#1a1200",
    border: "1px solid #5a4000",
    color: "#ffb74d",
    fontSize: 13,
    padding: "10px 24px",
    textAlign: "center",
  },
  main: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "0 24px 48px",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    gap: 20,
    flex: 1,
  },
  loading: {
    textAlign: "center",
    color: "#6b6b8a",
    padding: 60,
    fontSize: 16,
  },
  empty: {
    textAlign: "center",
    color: "#6b6b8a",
    padding: 60,
    fontSize: 15,
  },
  footer: {
    textAlign: "center",
    padding: "20px 24px",
    fontSize: 12,
    color: "#3a3a5a",
    borderTop: "1px solid #1a1a2e",
  },
};
