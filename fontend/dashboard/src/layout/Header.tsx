import { getTenant } from "../shared/auth";
import { logout } from "../shared/auth";

/**
 * Header Component
 * Hiển thị thông tin tenant, user controls
 */

export function Header() {
  const tenant = getTenant();

  return (
    <header
      className="header"
      style={{
        marginLeft: "250px",
        borderBottom: "1px solid #e5e5e5",
        padding: "15px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        backgroundColor: "#fff",
      }}
    >
      <div>
        {tenant && <span className="text-muted">Tenant: {tenant}</span>}
      </div>

      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
        <span className="text-muted" style={{ fontSize: "14px" }}>
          Admin
        </span>
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={logout}
          style={{ borderRadius: "4px" }}
        >
          Logout
        </button>
      </div>
    </header>
  );
}
