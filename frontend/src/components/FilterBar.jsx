const CLASSES = ["All", "AR", "SMG", "LMG", "Sniper", "Shotgun", "Marksman", "Pistol", "Melee"];

export default function FilterBar({ selected, onChange }) {
  return (
    <div style={styles.bar}>
      {CLASSES.map((cls) => (
        <button
          key={cls}
          style={{
            ...styles.chip,
            ...(selected === cls ? styles.chipActive : {}),
          }}
          onClick={() => onChange(cls)}
        >
          {cls}
        </button>
      ))}
    </div>
  );
}

const styles = {
  bar: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
    padding: "16px 24px",
    maxWidth: 1100,
    margin: "0 auto",
  },
  chip: {
    background: "#13131f",
    border: "1px solid #2a2a40",
    color: "#9090b0",
    borderRadius: 20,
    padding: "5px 14px",
    fontSize: 13,
    fontWeight: 500,
    transition: "all 0.15s",
  },
  chipActive: {
    background: "#1e1e3a",
    border: "1px solid #4fc3f7",
    color: "#4fc3f7",
  },
};
