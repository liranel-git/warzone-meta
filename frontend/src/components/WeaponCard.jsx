const TIER_COLORS = {
  "Absolute Meta": { accent: "#ffd700", bg: "rgba(255,215,0,0.06)", label: "🏆 ABSOLUTE META" },
  Meta:            { accent: "#00e676", bg: "rgba(0,230,118,0.06)", label: "🔥 META" },
  A:               { accent: "#4fc3f7", bg: "rgba(79,195,247,0.06)", label: "★ A TIER" },
  B:               { accent: "#ffb74d", bg: "rgba(255,183,77,0.06)",  label: "B TIER" },
  F:               { accent: "#ef5350", bg: "rgba(239,83,80,0.06)",   label: "💀 F TIER" },
};

const CLASS_ICONS = {
  AR: "🔫", SMG: "⚡", LMG: "🔩", Sniper: "🎯",
  Shotgun: "💥", Marksman: "🏹", Pistol: "🔘", Melee: "🗡",
};

export default function WeaponCard({ build }) {
  const t = TIER_COLORS[build.tier] ?? TIER_COLORS.B;

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

      <div style={styles.attachments}>
        {build.attachments.map((att, i) => (
          <span key={i} style={styles.attChip}>{att}</span>
        ))}
      </div>

      {build.reasoning && (
        <p style={styles.reasoning}>{build.reasoning}</p>
      )}

      <div style={styles.footer}>
        <span style={styles.source}>
          {build.source_type === "youtube" ? "▶ YouTube" : "💬 Reddit"}
          {build.source_title ? ` · ${build.source_title.slice(0, 48)}${build.source_title.length > 48 ? "…" : ""}` : ""}
        </span>
        {build.source_url && (
          <a href={build.source_url} target="_blank" rel="noreferrer" style={styles.sourceLink}>
            Source ↗
          </a>
        )}
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
    gap: 12,
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
  reasoning: {
    fontSize: 13,
    color: "#8080a0",
    fontStyle: "italic",
    lineHeight: 1.5,
  },
  footer: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    flexWrap: "wrap",
    marginTop: 4,
  },
  source: {
    fontSize: 11,
    color: "#555570",
    flex: 1,
  },
  sourceLink: {
    fontSize: 11,
    color: "#4fc3f7",
    textDecoration: "underline",
  },
  confidence: {
    fontSize: 11,
    fontWeight: 600,
  },
};
