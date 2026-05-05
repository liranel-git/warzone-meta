import { useState } from "react";
import NavBar from "../components/NavBar.jsx";
import Header from "../components/Header.jsx";

const CAMO_DATA = {
  "Black Ops 7": {
    color: "#ffd700",
    mastery: "Singularity",
    camos: [
      {
        name: "Base Camos", tier: 0,
        challenges: [
          "Kill 200 enemies", "Get 50 headshots", "Get 50 kills without dying 5 times",
          "Kill 25 enemies while ADS", "Get 15 longshot kills",
        ],
      },
      {
        name: "Infestation", tier: 1, color: "#00e676",
        challenges: [
          "Complete all Base Camos for this weapon",
          "Get 50 kills shortly after sprinting",
          "Kill 25 enemies from behind",
          "Get 30 double kills",
        ],
      },
      {
        name: "Genesis", tier: 2, color: "#4fc3f7",
        challenges: [
          "Complete Infestation camo",
          "Get 100 kills with no attachments",
          "Survive 10 matches without dying more than once",
          "Get 3 kills per life 10 times",
        ],
      },
      {
        name: "Apocalypse", tier: 3, color: "#ff6b6b",
        challenges: [
          "Complete Genesis camo",
          "Get 200 kills while on a killstreak",
          "Win 10 matches with this weapon equipped",
          "Get 5 kills per life 5 times",
        ],
      },
      {
        name: "Nexus Horizon", tier: 4, color: "#c084fc",
        challenges: [
          "Complete Apocalypse camo",
          "Reach max weapon level",
          "Get 500 kills total",
          "Complete a weapon prestige challenge",
        ],
      },
      {
        name: "Singularity ✦ MASTERY", tier: 5, color: "#ffd700",
        challenges: [
          "Earn Nexus Horizon on 36 weapons",
          "One camo to rule them all — the true endgame grind",
        ],
      },
    ],
  },
  "Black Ops 6": {
    color: "#00e676",
    mastery: "Dark Matter",
    camos: [
      {
        name: "Base Camos", tier: 0,
        challenges: [
          "Kill 150 enemies", "Get 50 headshots", "Get 50 bloodthirsty medals",
          "Get 25 longshot kills", "Kill 10 enemies while operator is low health",
        ],
      },
      {
        name: "Abyss", tier: 1, color: "#4fc3f7",
        challenges: [
          "Complete all Base Camos",
          "Get 50 mounted kills",
          "Kill 25 enemies in a single match 5 times",
          "Get 30 kills while crouching",
        ],
      },
      {
        name: "Nebula", tier: 2, color: "#c084fc",
        challenges: [
          "Complete Abyss",
          "Get 100 kills in hardcore modes",
          "Get 10 quad-feed medals",
          "Win 10 matches with this weapon in your primary slot",
        ],
      },
      {
        name: "Dark Matter ✦ MASTERY", tier: 3, color: "#ffd700",
        challenges: [
          "Earn Gold (Nebula) on every weapon in a weapon category",
          "Then earn Diamond across all categories",
          "The most prestigious camo in BO6 — requires grinding every weapon",
        ],
      },
    ],
  },
  "Modern Warfare III": {
    color: "#ffb74d",
    mastery: "Interstellar",
    camos: [
      {
        name: "Base Camos", tier: 0,
        challenges: [
          "Kill 50 enemies", "Kill 10 enemies while ADS", "Kill 10 enemies crouching",
          "Get 10 headshots", "Get 10 longshots",
        ],
      },
      {
        name: "Borealis", tier: 1, color: "#4fc3f7",
        challenges: [
          "Complete 50 operator kills total",
          "Get 10 kills in a single match",
          "Get 5 kills without dying 10 times",
          "Earn Gold on 3 weapons in this category",
        ],
      },
      {
        name: "Interstellar ✦ MASTERY", tier: 2, color: "#ffd700",
        challenges: [
          "Earn Borealis (Platinum equivalent) on every weapon class",
          "The MW3 endgame grind — requires Gold on all weapons per class",
        ],
      },
    ],
  },
  "Modern Warfare II": {
    color: "#6b6b8a",
    mastery: "Orion",
    camos: [
      {
        name: "Base Camos", tier: 0,
        challenges: ["Kill 100 enemies", "Get 25 headshots", "Get 10 kills while ADS", "5 mounted kills"],
      },
      {
        name: "Bioluminescent", tier: 1, color: "#00e676",
        challenges: [
          "Earn Platinum on all weapons in 2 categories",
          "Complete the associated weapon challenges",
        ],
      },
      {
        name: "Orion ✦ MASTERY", tier: 2, color: "#ffd700",
        challenges: [
          "Earn Bioluminescent on every weapon class",
          "One of the rarest camos — requires mastering every weapon in the game",
        ],
      },
    ],
  },
};

export default function CamoHubPage() {
  const [activeGame, setActiveGame] = useState("Black Ops 7");

  const game = CAMO_DATA[activeGame];

  return (
    <div style={styles.page}>
      <Header />
      <NavBar />
      <main style={styles.main}>
        <h2 style={styles.heading}>Camo Hub</h2>
        <p style={styles.sub}>Mastery camo progression paths for every active CoD title.</p>

        <div style={styles.gameTabs}>
          {Object.keys(CAMO_DATA).map((g) => (
            <button
              key={g}
              style={{
                ...styles.gameTab,
                ...(activeGame === g ? { ...styles.gameTabActive, borderColor: CAMO_DATA[g].color, color: CAMO_DATA[g].color } : {}),
              }}
              onClick={() => setActiveGame(g)}
            >
              {g}
            </button>
          ))}
        </div>

        <div style={styles.masteryBadge}>
          <span style={{ color: game.color, fontFamily: "Rajdhani, sans-serif", fontSize: 20, fontWeight: 700 }}>
            ✦ Mastery Camo: {game.mastery}
          </span>
        </div>

        <div style={styles.track}>
          {game.camos.map((stage, i) => (
            <div key={stage.name} style={styles.stage}>
              <div style={styles.stageHeader}>
                <div style={{ ...styles.dot, background: stage.color ?? "#3a3a5a" }} />
                {i < game.camos.length - 1 && <div style={styles.line} />}
                <span style={{ ...styles.stageName, color: stage.color ?? "#e8e8f0" }}>
                  {stage.name}
                </span>
                {stage.tier > 0 && (
                  <span style={{ ...styles.tierBadge, borderColor: stage.color ?? "#3a3a5a", color: stage.color ?? "#6b6b8a" }}>
                    Tier {stage.tier}
                  </span>
                )}
              </div>
              <div style={styles.challenges}>
                {stage.challenges.map((c, j) => (
                  <div key={j} style={styles.challenge}>▸ {c}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#0d0d14" },
  main: { maxWidth: 900, margin: "0 auto", padding: "32px 24px 64px" },
  heading: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 32, fontWeight: 700,
    color: "#fff", letterSpacing: "0.06em", margin: "0 0 8px",
  },
  sub: { fontSize: 13, color: "#6b6b8a", margin: "0 0 32px" },
  gameTabs: { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 24 },
  gameTab: {
    background: "#12121e", border: "1px solid #2a2a40",
    color: "#6b6b8a", borderRadius: 8, padding: "8px 18px",
    fontSize: 13, fontWeight: 600, cursor: "pointer",
  },
  gameTabActive: { background: "#1a1a2e" },
  masteryBadge: {
    background: "#12121e", border: "1px solid #2a2a40",
    borderRadius: 10, padding: "12px 20px", marginBottom: 32,
  },
  track: { display: "flex", flexDirection: "column", gap: 0 },
  stage: {
    paddingLeft: 32,
    paddingBottom: 24,
    position: "relative",
  },
  stageHeader: { display: "flex", alignItems: "center", gap: 10, marginBottom: 10 },
  dot: { width: 12, height: 12, borderRadius: "50%", flexShrink: 0, marginLeft: -38 },
  line: {
    position: "absolute", left: -32, top: 20, bottom: 0,
    width: 1, background: "#2a2a40",
  },
  stageName: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 17, fontWeight: 700, letterSpacing: "0.04em",
  },
  tierBadge: {
    fontSize: 10, fontWeight: 700, border: "1px solid",
    borderRadius: 4, padding: "2px 8px", letterSpacing: "0.06em",
  },
  challenges: { display: "flex", flexDirection: "column", gap: 4 },
  challenge: { fontSize: 13, color: "#6b6b8a", lineHeight: 1.6, paddingLeft: 4 },
};
