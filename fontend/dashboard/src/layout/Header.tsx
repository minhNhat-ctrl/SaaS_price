import { Link } from "react-router-dom";
import { useAuth } from "../shared/AuthContext";

/**
 * Header Component
 * Hiển thị thông tin user, controls
 */

export function Header() {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <header
      className="header"
      style={{
        borderBottom: "1px solid #e5e5e5",
        padding: "15px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        backgroundColor: "#fff",
      }}
    >
      <div>
        <h5 className="mb-0">PriceSync Dashboard</h5>
      </div>

      <div style={{ display: "flex", gap: "15px", alignItems: "center" }}>
        <Link 
          to="/profile" 
          className="text-decoration-none"
          style={{ fontSize: "14px" }}
        >
          <i className="bi bi-person-circle me-1"></i>
          {user?.email}
        </Link>
        <button
          className="btn btn-sm btn-outline-danger"
          onClick={handleLogout}
          style={{ borderRadius: "4px" }}
        >
          <i className="bi bi-box-arrow-right me-1"></i>
          Logout
        </button>
      </div>
    </header>
  );
}
