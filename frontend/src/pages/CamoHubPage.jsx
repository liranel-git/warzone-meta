import { useState, useEffect, useCallback } from "react";
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

function lsKey(game, weapon, stageName) {
  return `camo|${game}|${weapon.trim().toLowerCase()}|${stageName}`;
}

function loadChecked(game, weapon, stageName, count) {
  if (!weapon.trim()) return new Array(count).fill(false);
  try {
    const raw = localStorage.getItem(lsKey(game, weapon, stageName));
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length === count) return arr;
    }
  } catch {}
  return new Array(count).fill(false);
}

function saveChecked(game, weapon, stageName, arr) {
  if (!weapon.trim()) return;
  localStorage.setItem(lsKey(game, weapon, stageName), JSON.stringify(arr));
}

function ProgressBar({ done, total, color }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <div style={pbStyles.wrap}>
      <div style={{ ...pbStyles.track }}>
        <div style={{ ...pbStyles.fill, width: `${pct}%`, background: color ?? "#4fc3f7" }} />
      </div>
      <span style={pbStyles.label}>{done}/{total}</span>
    </div>
  );
}
const pbStyles = {
  wrap: { display: "flex", alignItems: "center", gap: 8, marginTop: 6 },
  track: { flex: 1, height: 4, background: "#1e1e30", borderRadius: 2, overflow: "hidden" },
  fill: { height: "100%", borderRadius: 2, transition: "width 0.2s" },
  label: { fontSize: 11, color: "#6b6b8a", minWidth: 32, textAlign: "right" },
};

function StageTracker({ game, weapon, stage }) {
  const [checked, setChecked] = useState(() =>
    loadChecked(game, weapon, stage.name, stage.challenges.length)
  );

  useEffect(() => {
    const next = loadChecked(game, weapon, stage.name, stage.challenges.length);
    setChecked(next);
  }, [game, weapon, stage.name, stage.challenges.length]);

  const toggle = useCallback((i) => {
    setChecked((prev) => {
      const next = [...prev];
      next[i] = !next[i];
      saveChecked(game, weapon, stage.name, next);
      return next;
    });
  }, [game, weapon, stage.name]);

  const done = checked.filter(Boolean).length;
  const color = stage.color ?? "#3a3a5a";

  return (
    <div style={styles.stage}>
      <div style={styles.stageHeader}>
        <div style={{ ...styles.dot, background: color }} />
        <span style={{ ...styles.stageName, color: stage.tier === 0 ? "#e8e8f0" : color }}>
          {stage.name}
        </span>
        {stage.tier > 0 && (
          <span style={{ ...styles.tierBadge, borderColor: color, color }}>
            Tier {stage.tier}
          </span>
        )}
        {weapon.trim() && (
          <span style={{ marginLeft: "auto", fontSize: 11, color: done === stage.challenges.length ? "#00e676" : "#4a4a6a", fontWeight: 700 }}>
            {done === stage.challenges.length ? "✓ DONE" : `${done}/${stage.challenges.length}`}
          </span>
        )}
      </div>

      {weapon.trim() && (
        <ProgressBar done={done} total={stage.challenges.length} color={color} />
      )}

      <div style={styles.challenges}>
        {stage.challenges.map((c, j) => (
          <label key={j} style={styles.challenge}>
            {weapon.trim() ? (
              <input
                type="checkbox"
                checked={checked[j]}
                onChange={() => toggle(j)}
                style={styles.checkbox}
              />
            ) : (
              <span style={styles.bullet}>▸</span>
            )}
            <span style={{ ...styles.challengeText, textDecoration: checked[j] && weapon.trim() ? "line-through" : "none", color: checked[j] && weapon.trim() ? "#3a3a5a" : "#6b6b8a" }}>
              {c}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

export default function CamoHubPage() {
  const [activeGame, setActiveGame] = useState("Black Ops 7");
  const [weapon, setWeapon] = useState("");

  const game = CAMO_DATA[activeGame];

  const totalChallenges = game.camos.reduce((s, st) => s + st.challenges.length, 0);
  const completedChallenges = weapon.trim()
    ? game.camos.reduce((s, st) => {
        const arr = loadChecked(activeGame, weapon, st.name, st.challenges.length);
        return s + arr.filter(Boolean).length;
      }, 0)
    : 0;

  const [, forceUpdate] = useState(0);
  const handleWeaponChange = (v) => {
    setWeapon(v);
    forceUpdate((n) => n + 1);
  };

  return (
    <div style={styles.page}>
      <Header />
      <NavBar />
      <main style={styles.main}>
        <h2 style={styles.heading}>Camo Hub</h2>
        <p style={styles.sub}>Track your mastery camo grind per weapon, per game.</p>

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

        <div style={styles.weaponRow}>
          <div style={styles.inputWrap}>
            <span style={styles.inputIcon}>🔫</span>
            <input
              style={styles.weaponInput}
              type="text"
              placeholder="Enter weapon name to track (e.g. Voyak KT-3)"
              value={weapon}
              onChange={(e) => handleWeaponChange(e.target.value)}
            />
            {weapon && (
              <button style={styles.clearBtn} onClick={() => handleWeaponChange("")}>✕</button>
            )}
          </div>
        </div>

        {weapon.trim() && (
          <div style={styles.overallCard}>
            <div style={styles.overallLabel}>
              <span style={{ color: game.color, fontFamily: "Rajdhani, sans-serif", fontWeight: 700, fontSize: 15 }}>
                {weapon} — {activeGame}
              </span>
              <span style={{ color: completedChallenges === totalChallenges ? "#00e676" : "#6b6b8a", fontSize: 13 }}>
                {completedChallenges === totalChallenges ? "✦ COMPLETE" : `${completedChallenges} / ${totalChallenges} challenges`}
              </span>
            </div>
            <ProgressBar done={completedChallenges} total={totalChallenges} color={game.color} />
          </div>
        )}

        <div style={styles.masteryBadge}>
          <span style={{ color: game.color, fontFamily: "Rajdhani, sans-serif", fontSize: 18, fontWeight: 700 }}>
            ✦ Mastery Camo: {game.mastery}
          </span>
        </div>

        <div style={styles.track}>
          {game.camos.map((stage) => (
            <StageTracker
              key={`${activeGame}|${weapon}|${stage.name}`}
              game={activeGame}
              weapon={weapon}
              stage={stage}
            />
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
  weaponRow: { marginBottom: 20 },
  inputWrap: {
    display: "flex", alignItems: "center", gap: 0,
    background: "#12121e", border: "1px solid #2a2a40",
    borderRadius: 10, padding: "0 12px", maxWidth: 480,
  },
  inputIcon: { fontSize: 16, marginRight: 8 },
  weaponInput: {
    flex: 1, background: "none", border: "none", outline: "none",
    color: "#e8e8f0", fontSize: 14, padding: "11px 0",
  },
  clearBtn: {
    background: "none", border: "none", color: "#4a4a6a",
    fontSize: 14, cursor: "pointer", padding: "0 4px",
  },
  overallCard: {
    background: "#12121e", border: "1px solid #2a2a40",
    borderRadius: 10, padding: "14px 18px", marginBottom: 20,
  },
  overallLabel: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
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
  stageName: {
    fontFamily: "Rajdhani, sans-serif", fontSize: 17, fontWeight: 700, letterSpacing: "0.04em",
  },
  tierBadge: {
    fontSize: 10, fontWeight: 700, border: "1px solid",
    borderRadius: 4, padding: "2px 8px", letterSpacing: "0.06em",
  },
  challenges: { display: "flex", flexDirection: "column", gap: 6 },
  challenge: {
    display: "flex", alignItems: "flex-start", gap: 8, cursor: "pointer",
  },
  checkbox: { marginTop: 2, cursor: "pointer", accentColor: "#4fc3f7", flexShrink: 0 },
  bullet: { color: "#4a4a6a", marginTop: 1, flexShrink: 0 },
  challengeText: { fontSize: 13, lineHeight: 1.6, transition: "color 0.15s" },
};
