import { useState } from "react";

const TIER_COLORS = {
  "Absolute Meta": { accent: "#ffd700", bg: "rgba(255,215,0,0.06)", label: "🏆 ABSOLUTE META" },
  Meta:            { accent: "#00e676", bg: "rgba(0,230,118,0.06)", label: "🔥 META" },
  A:               { accent: "#4fc3f7", bg: "rgba(79,195,247,0.06)", label: "★ A TIER" },
  B:               { accent: "#ffb74d", bg: "rgba(255,183,77,0.06)",  label: "B TIER" },
  F:               { accent: "#ef5350", bg: "rgba(239,83,80,0.06)",   label: "💀 F TIER" },
};

const CLASS_ICONS = {
  AR: "🔫", SMG: "⚡", LMG: "🔩", Sniper: "🎯",
  Shotgun: "💥", Marksman: "🏹", Pistol: "🔘",
};

const DOMINANCY_MAPS = {
  "Long Range":     ["Verdansk", "Haven's Hollow"],
  "Sniper":         ["Verdansk"],
  "Support":        ["Verdansk", "Haven's Hollow"],
  "Lowest Recoil":  ["Verdansk", "Haven's Hollow"],
  "Close Range":    ["Astra Malorum", "Haven's Hollow"],
  "Hip Fire":       ["Astra Malorum"],
  "Aggressive":     ["Astra Malorum", "Haven's Hollow"],
};

export default function WeaponCard({ build }) {
  const [showMaps, setShowMaps] = useState(false);
  const t = TIER_COLORS[build.tier] ?? TIER_COLORS.B;
  const dominancy = build.weapon_dominancy;
  const bestMaps = dominancy ? DOMINANCY_MAPS[dominancy] : null;

  return (
    <div style={{ ...styles.card, borderColor: t.accent, background: `linear-gradient(135deg, ${t.bg}, #13131f)` }}>
      <div style={styles.top}>
        <div style={styles.nameRow}>
          <span style={styles.classIcon}>{CLASS_ICONS[build.weapon_class] ?? "🔫"}</span>
          <h3 style={styles.weaponName}>{build.weapon_name}</h3>
          <span style={{ ...styles.tierBadge, color: t.accent, borderColor: t.accent }}>
            {t.label}
          </span>
        </div>
        <span style={styles.classTag}>{build.weapon_class}</span>
      </div>

      <div style={styles.metaRow}>
        {build.play_style && (
          <span style={styles.playStyleTag}>📺 {build.play_style}</span>
        )}
        {dominancy && (
          <span style={styles.dominancyTag}>{dominancy}</span>
        )}
      </div>

      <div style={styles.attachments}>
        {build.attachments.map((att, i) => (
          <span key={i} style={styles.attChip}>{att}</span>
        ))}
      </div>

      {bestMaps && (
        <div>
          <button style={styles.toggle} onClick={() => setShowMaps(!showMaps)}>
            {showMaps ? "▾ Best Maps" : "▸ Best Maps"}
          </button>
          {showMaps && (
            <div style={styles.mapsRow}>
              {bestMaps.map((m) => (
                <span key={m} style={styles.mapChip}>🗺 {m}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={styles.footer}>
        <span style={{ ...styles.confidence, color: build.confidence >= 0.85 ? "#00e676" : build.confidence >= 0.65 ? "#ffb74d" : "#ef5350" }}>
          {Math.round(build.confidence * 100)}% confidence
        </span>
      </div>
    </div>
  );
}

const styles = {
  card: {
    border: "1px solid",
    borderRadius: 12,
    padding: "18px 20px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    transition: "transform 0.15s",
  },
  top: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 8,
  },
  nameRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap",
  },
  classIcon: { fontSize: 20 },
  weaponName: {
    fontFamily: "Rajdhani, sans-serif",
    fontSize: 22,
    fontWeight: 700,
    color: "#fff",
    letterSpacing: "0.04em",
  },
  tierBadge: {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.08em",
    border: "1px solid",
    borderRadius: 4,
    padding: "2px 8px",
  },
  classTag: {
    fontSize: 11,
    color: "#6b6b8a",
    background: "#1a1a2e",
    borderRadius: 4,
    padding: "2px 8px",
    flexShrink: 0,
  },
  metaRow: { display: "flex", gap: 6, flexWrap: "wrap" },
  playStyleTag: {
    background: "#1a2236", border: "1px solid #2a3a55", color: "#9bb8e0",
    borderRadius: 6, padding: "3px 10px", fontSize: 11,
    fontWeight: 600, letterSpacing: "0.03em",
  },
  dominancyTag: {
    background: "#1a1a2e", border: "1px solid #2a2a40", color: "#9090b0",
    borderRadius: 6, padding: "3px 10px", fontSize: 11,
  },
  attachments: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  attChip: {
    background: "#1a1a2e",
    border: "1px solid #2a2a40",
    borderRadius: 6,
    padding: "3px 10px",
    fontSize: 12,
    color: "#c0c0d8",
  },
  mapsRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 6,
    alignItems: "center",
  },
  mapChip: {
    background: "#0d1f2a",
    border: "1px solid #1a3a4a",
    borderRadius: 6,
    padding: "3px 10px",
    fontSize: 12,
    color: "#4fc3f7",
  },
  toggle: {
    background: "none",
    border: "none",
    color: "#4fc3f7",
    fontSize: 12,
    cursor: "pointer",
    padding: 0,
    fontWeight: 600,
  },
  footer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 12,
    flexWrap: "wrap",
    marginTop: 4,
  },
  confidence: {
    fontSize: 11,
    fontWeight: 600,
  },
};
