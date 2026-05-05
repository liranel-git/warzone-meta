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
    },
    {
      name: "Haven's Hollow",
      image: "🌲",
      desc: "A new mid-size BR map introduced in BO7. Dense forest areas with tight urban pockets create a fast-paced experience with more frequent engagements than Verdansk.",
      size: "Medium (BR)",
      players: "Up to 100",
      tips: ["Forest areas favour snipers — keep moving", "Urban pockets reward SMG loadouts", "Central compound is heavily contested every match"],
    },
    {
      name: "Astra Malorum",
      image: "🌑",
      desc: "A dark, atmospheric map set in a corrupted zone. Tight corridors and minimal cover make it one of the most intense Warzone experiences. Also used in BO7 Zombies.",
      size: "Small (Resurgence)",
      players: "Up to 60",
      tips: ["Shotguns and SMGs dominate", "Stay out of open areas — very little cover", "Rooftops are dangerous but offer great sight lines"],
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
    },
    {
      name: "Shattered Veil",
      image: "🌿",
      desc: "A sprawling manor and estate map with multiple interconnected zones. More complex layout rewards experienced Zombies players.",
      size: "Large",
      players: "1–4 Co-op",
      tips: ["The greenhouse area is safest for training", "Multiple Pack-a-Punch locations reduce bottlenecks", "Salvage farming is efficient in the east wing"],
    },
    {
      name: "The Tomb",
      image: "⚰️",
      desc: "Ancient ruins with a dark, oppressive atmosphere. Introduces new enemy variants and the most complex easter egg of the BO6 Zombies lineup.",
      size: "Medium",
      players: "1–4 Co-op",
      tips: ["Tight corridors punish slow play — keep moving", "LMGs shine here for ammo economy", "Main quest easter egg requires full team coordination"],
    },
  ],
};

export default function MapsHubPage() {
  return (
    <div style={styles.page}>
      <Header />
      <NavBar />
      <main style={styles.main}>
        <h2 style={styles.heading}>Maps Hub</h2>
        <p style={styles.sub}>Current maps across Warzone, BO7, and BO6 — with tips for each.</p>
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
                  <div style={styles.tips}>
                    <div style={styles.tipsLabel}>Tips</div>
                    {map.tips.map((tip, i) => (
                      <div key={i} style={styles.tip}>• {tip}</div>
                    ))}
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
  tips: { borderTop: "1px solid #1e1e30", paddingTop: 10 },
  tipsLabel: { fontSize: 11, color: "#4fc3f7", fontWeight: 700, letterSpacing: "0.06em", marginBottom: 6 },
  tip: { fontSize: 12, color: "#6b6b8a", lineHeight: 1.6 },
};
