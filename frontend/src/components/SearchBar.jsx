export default function SearchBar({ value, onChange }) {
  return (
    <div style={styles.wrapper}>
      <span style={styles.icon}>🔍</span>
      <input
        style={styles.input}
        type="text"
        placeholder="Search weapons…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && (
        <button style={styles.clear} onClick={() => onChange("")}>✕</button>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    alignItems: "center",
    background: "#13131f",
    border: "1px solid #2a2a40",
    borderRadius: 10,
    padding: "0 12px",
    gap: 8,
    maxWidth: 340,
    width: "100%",
  },
  icon: {
    fontSize: 14,
    opacity: 0.5,
  },
  input: {
    background: "none",
    border: "none",
    outline: "none",
    color: "#e8e8f0",
    fontSize: 14,
    padding: "9px 0",
    flex: 1,
    minWidth: 0,
  },
  clear: {
    background: "none",
    border: "none",
    color: "#6b6b8a",
    fontSize: 13,
    cursor: "pointer",
    padding: "0 2px",
    lineHeight: 1,
  },
};
