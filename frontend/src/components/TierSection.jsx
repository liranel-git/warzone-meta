import WeaponCard from "./WeaponCard.jsx";

const TIER_META = {
  "Absolute Meta": {
    color: "#ffd700",
    desc: "The undisputed kings. Run these or get cooked.",
    glow: "0 0 30px rgba(255,215,0,0.15)",
  },
  Meta: {
    color: "#00e676",
    desc: "Top-tier. Highly competitive across all scenarios.",
    glow: "0 0 30px rgba(0,230,118,0.1)",
  },
  A: {
    color: "#4fc3f7",
    desc: "Solid picks. Viable and won't let you down.",
    glow: "none",
  },
  B: {
    color: "#ffb74d",
    desc: "Below average. Situational at best.",
    glow: "none",
  },
  F: {
    color: "#ef5350",
    desc: "Avoid. Outclassed or nerfed into the ground.",
    glow: "none",
  },
};

export default function TierSection({ tier, builds }) {
  if (!builds.length) return null;
  const meta = TIER_META[tier] ?? { color: "#fff", desc: "", glow: "none" };

  return (
    <section style={{ ...styles.section, boxShadow: meta.glow }}>
      <div style={styles.header}>
        <div style={{ ...styles.tierBar, background: meta.color }} />
        <div>
          <h2 style={{ ...styles.tierName, color: meta.color }}>{tier}</h2>
          <p style={styles.tierDesc}>{meta.desc}</p>
        </div>
        <span style={{ ...styles.count, color: meta.color }}>
          {builds.length} {builds.length === 1 ? "build" : "builds"}
        </span>
      </div>

      <div style={styles.grid}>
        {builds.map((b) => (
          <WeaponCard key={b.id} build={b} />
        ))}
      </div>
    </section>
  );
}

const styles = {
  section: {
    background: "#13131f",
    border: "1px solid #2a2a40",
    borderRadius: 14,
    padding: "20px 22px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    marginBottom: 18,
  },
  tierBar: {
    width: 4,
    height: 44,
    borderRadius: 2,
    flexShrink: 0,
  },
  tierName: {
    fontFamily: "Rajdhani, sans-serif",
    fontSize: 24,
    fontWeight: 700,
    letterSpacing: "0.06em",
    lineHeight: 1,
  },
  tierDesc: {
    fontSize: 12,
    color: "#6b6b8a",
    marginTop: 3,
  },
  count: {
    marginLeft: "auto",
    fontFamily: "Rajdhani, sans-serif",
    fontSize: 20,
    fontWeight: 700,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
    gap: 14,
  },
};
