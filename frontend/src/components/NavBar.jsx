import { useNavigate, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { label: "META BUILDS", path: "/" },
];

export default function NavBar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <nav style={styles.nav}>
      <div style={styles.inner}>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.path;
          return (
            <button
              key={item.path}
              style={{ ...styles.item, ...(active ? styles.active : {}) }}
              onClick={() => navigate(item.path)}
            >
              {item.label}
              {active && <span style={styles.underline} />}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

const styles = {
  nav: {
    background: "#0a0a18",
    borderBottom: "1px solid #1a1a2e",
  },
  inner: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "0 24px",
    display: "flex",
    gap: 4,
  },
  item: {
    background: "none",
    border: "none",
    color: "#6b6b8a",
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: "0.1em",
    padding: "12px 16px",
    cursor: "pointer",
    position: "relative",
    transition: "color 0.15s",
    fontFamily: "Rajdhani, sans-serif",
  },
  active: {
    color: "#4fc3f7",
  },
  underline: {
    position: "absolute",
    bottom: 0,
    left: 16,
    right: 16,
    height: 2,
    background: "#4fc3f7",
    borderRadius: 2,
    display: "block",
  },
};
