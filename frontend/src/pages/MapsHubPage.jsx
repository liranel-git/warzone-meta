import NavBar from "../components/NavBar.jsx";
import Header from "../components/Header.jsx";

const MAPS = {
  Warzone: [
    {
      name: "Verdansk",
      image: "🏙️",
      desc: "The classic 150-player battle royale map, rebuilt from the ground up for BO7. Iconic landmarks like Verdansk Airport, Hospital, and Stadium return with updated visuals.",
      size: "Large (BR)",
      players: "Up to 150",
      tips: ["Hospital rooftop is a power position", "Stadium interior has multiple entry points", "Downtown is a hot drop — expect early fights"],
      bestStyles: ["Long Range", "Sniper", "Support", "Lowest Recoil"],
      bestWeapons: [
        { name: "Voyak KT-3", cls: "AR", tier: "Absolute Meta" },
        { name: "Strider 300", cls: "Sniper", tier: "Absolute Meta" },
        { name: "MK.78", cls: "LMG", tier: "Meta" },
        { name: "MK35 ISR", cls: "Sniper", tier: "Meta" },
      ],
    },
    {
      name: "Haven's Hollow",
      image: "🌲",
      desc: "A new mid-size BR map introduced in BO7. Dense forest areas with tight urban pockets create a fast-paced experience with more frequent engagements than Verdansk.",
      size: "Medium (BR)",
      players: "Up to 100",
      tips: ["Forest areas favour snipers — keep moving", "Urban pockets reward SMG loadouts", "Central compound is heavily contested every match"],
      bestStyles: ["Long Range", "Close Range", "Support", "Aggressive"],
      bestWeapons: [
        { name: "Voyak KT-3", cls: "AR", tier: "Absolute Meta" },
        { name: "VST", cls: "SMG", tier: "Absolute Meta" },
        { name: "Dravec 45", cls: "SMG", tier: "Meta" },
        { name: "Razor 9mm", cls: "SMG", tier: "Meta" },
      ],
    },
    {
      name: "Astra Malorum",
      image: "🌑",
      desc: "A dark, atmospheric small resurgence map set in a corrupted zone. Tight corridors and minimal cover make it the most aggressive Warzone experience.",
      size: "Small (Resurgence)",
      players: "Up to 60",
      tips: ["Shotguns and SMGs dominate", "Stay out of open areas — very little cover", "Rooftops are dangerous but offer great sight lines"],
      bestStyles: ["Close Range", "Hip Fire", "Aggressive"],
      bestWeapons: [
        { name: "VST", cls: "SMG", tier: "Absolute Meta" },
        { name: "DS20 Mirage", cls: "SMG", tier: "Absolute Meta" },
        { name: "SG-12", cls: "Shotgun", tier: "A" },
        { name: "Sturmwolf 45", cls: "SMG", tier: "Meta" },
      ],
    },
  ],
  "BO7 Multiplayer": [
    {
      name: "Avalon",
      image: "🏝️",
      desc: "The BO7 endgame map. Tropical setting with a mix of open areas and tight interiors. Designed for intense 6v6 combat.",
      size: "Medium (6v6)",
      players: "12",
      tips: ["Mid lane control wins most modes", "Flanking routes on the outside are underused", "Hardpoint rotations favour the high-ground team"],
      bestStyles: ["Close Range", "Aggressive", "Support"],
      bestWeapons: [
        { name: "VST", cls: "SMG", tier: "Absolute Meta" },
        { name: "Voyak KT-3", cls: "AR", tier: "Absolute Meta" },
        { name: "EGRT-17", cls: "AR", tier: "Meta" },
      ],
    },
  ],
  "BO7 Zombies": [
    {
      name: "Astra Malorum",
      image: "🧟",
      desc: "The flagship BO7 Zombies map. The story continues in the corrupted Astra dimension with new enemy types, easter eggs, and a full main quest.",
      size: "Open World",
      players: "1–4 Co-op",
      tips: ["Pack-a-Punch is located in the central spire", "Salvage early for free upgrades", "Round 30+ needs a Wonder Weapon — prioritise the main quest"],
      bestStyles: ["Close Range", "Hip Fire"],
      bestWeapons: [
        { name: "VST", cls: "SMG", tier: "Absolute Meta" },
        { name: "MK.78", cls: "LMG", tier: "Meta" },
      ],
    },
  ],
  "BO6 Zombies": [
    {
      name: "Liberty Falls",
      image: "🏘️",
      desc: "Small-town America overrun by the undead. One of the most accessible Zombies maps ever made with a tight layout and straightforward easter egg.",
      size: "Small",
      players: "1–4 Co-op",
      tips: ["Circle runs around Main Street are efficient", "Church area has the best cover for high rounds", "Easy easter egg — great for camo grinding"],
      bestStyles: ["Close Range", "Hip Fire"],
      bestWeapons: [
        { name: "XM4", cls: "AR", tier: "A" },
        { name: "LC10", cls: "SMG", tier: "A" },
      ],
    },
    {
      name: "Shattered Veil",
      image: "🌿",
      desc: "A sprawling manor and estate map with multiple interconnected zones. More complex layout rewards experienced Zombies players.",
      size: "Large",
      players: "1–4 Co-op",
      tips: ["The greenhouse area is safest for training", "Multiple Pack-a-Punch locations reduce bottlenecks", "Salvage farming is efficient in the east wing"],
      bestStyles: ["Long Range", "Support"],
      bestWeapons: [
        { name: "MK.78", cls: "LMG", tier: "Meta" },
        { name: "Voyak KT-3", cls: "AR", tier: "Absolute Meta" },
      ],
    },
    {
      name: "The Tomb",
      image: "⚰️",
      desc: "Ancient ruins with a dark, oppressive atmosphere. Introduces new enemy variants and the most complex easter egg of the BO6 Zombies lineup.",
      size: "Medium",
      players: "1–4 Co-op",
      tips: ["Tight corridors punish slow play — keep moving", "LMGs shine here for ammo economy", "Main quest easter egg requires full team coordination"],
      bestStyles: ["Hip Fire", "Close Range"],
      bestWeapons: [
        { name: "MK.78", cls: "LMG", tier: "Meta" },
        { name: "Razor 9mm", cls: "SMG", tier: "Meta" },
      ],
    },
  ],
};

const TIER_COLORS = {
  "Absolute Meta": "#ffd700",
  "Meta": "#00e676",
  "A": "#4fc3f7",
  "B": "#ffb74d",
};

export default function MapsHubPage() {
  return (
    <div style={styles.page}>
      <Header />
      <NavBar />
      <main style={styles.main}>
        <h2 style={styles.heading}>Maps Hub</h2>
        <p style={styles.sub}>Current maps across Warzone, BO7, and BO6 — with tips and recommended loadouts.</p>
        {Object.entries(MAPS).map(([game, maps]) => (
          <section key={game} style={styles.section}>
            <h3 style={styles.gameTitle}>{game}</h3>
            <div style={styles.grid}>
              {maps.map((map) => (
                <div key={map.name} style={styles.card}>
                  <div style={styles.cardTop}>
                    <span style={styles.emoji}>{map.image}</span>
                    <div>
                      <h4 style={styles.mapName}>{map.name}</h4>
                      <div style={styles.meta}>
                        <span style={styles.tag}>{map.size}</span>
                        <span style={styles.tag}>👥 {map.players}</span>
                      </div>
                    </div>
                  </div>
                  <p style={styles.desc}>{map.desc}</p>

                  <div style={styles.tipsSection}>
                    <div style={styles.sectionLabel}>Tips</div>
                    {map.tips.map((tip, i) => (
                      <div key={i} style={styles.tip}>• {tip}</div>
                    ))}
                  </div>

                  <div style={styles.loadoutsSection}>
                    <div style={styles.sectionLabel}>Best Loadouts</div>
                    <div style={styles.styleChips}>
                      {map.bestStyles.map((s) => (
                        <span key={s} style={styles.styleChip}>{s}</span>
                      ))}
                    </div>
                    <div style={styles.weaponList}>
                      {map.bestWeapons.map((w) => (
                        <div key={w.name} style={styles.weaponRow}>
                          <span style={styles.weaponName}>{w.name}</span>
                          <span style={styles.weaponCls}>{w.cls}</span>
                          <span style={{ ...styles.weaponTier, color: TIER_COLORS[w.tier] ?? "#6b6b8a" }}>
                            {w.tier}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
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
  sub: { fontSize: 13, color: "#6b6b8a", margin: "0 0 40px" },
  section: { marginBottom: 48 },
  gameTitle: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 18, fontWeight: 700,
    color: "#4fc3f7", letterSpacing: "0.08em", textTransform: "uppercase",
    margin: "0 0 16px", paddingBottom: 8, borderBottom: "1px solid #1a1a2e",
  },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 },
  card: {
    background: "#12121e", border: "1px solid #2a2a40", borderRadius: 12,
    padding: "20px 20px 16px", display: "flex", flexDirection: "column", gap: 12,
  },
  cardTop: { display: "flex", alignItems: "flex-start", gap: 14 },
  emoji: { fontSize: 32, lineHeight: 1, marginTop: 2 },
  mapName: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 20, fontWeight: 700,
    color: "#fff", margin: 0,
  },
  meta: { display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" },
  tag: {
    fontSize: 11, color: "#6b6b8a", background: "#1a1a2e",
    borderRadius: 4, padding: "2px 8px",
  },
  desc: { fontSize: 13, color: "#8080a0", lineHeight: 1.6, margin: 0 },
  tipsSection: { borderTop: "1px solid #1e1e30", paddingTop: 10 },
  loadoutsSection: { borderTop: "1px solid #1e1e30", paddingTop: 10 },
  sectionLabel: {
    fontSize: 11, color: "#4fc3f7", fontWeight: 700,
    letterSpacing: "0.06em", marginBottom: 8, textTransform: "uppercase",
  },
  tip: { fontSize: 12, color: "#6b6b8a", lineHeight: 1.6 },
  styleChips: { display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 },
  styleChip: {
    background: "#0d1f2a", border: "1px solid #1a3a4a",
    borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#4fc3f7",
  },
  weaponList: { display: "flex", flexDirection: "column", gap: 4 },
  weaponRow: { display: "flex", alignItems: "center", gap: 8 },
  weaponName: { fontSize: 13, color: "#c0c0d8", flex: 1, fontWeight: 600 },
  weaponCls: {
    fontSize: 10, color: "#6b6b8a", background: "#1a1a2e",
    borderRadius: 3, padding: "1px 6px",
  },
  weaponTier: { fontSize: 11, fontWeight: 700 },
};
