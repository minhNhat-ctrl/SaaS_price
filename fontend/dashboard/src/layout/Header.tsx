import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../shared/AuthContext";

/**
 * Header Component
 * Responsive header: mobile collapsible, desktop full info
 * Hiển thị user, breadcrumb, tenant
 */

export function Header() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = "/login";
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  // Simple breadcrumb logic
  const getBreadcrumb = () => {
    const pathMap: Record<string, string> = {
      "/": "Dashboard",
      "/catalog": "Catalog",
      "/products": "Products",
      "/profile": "Profile",
    };
    return pathMap[location.pathname] || "Page";
  };

  return (
    <header className="bg-white border-bottom sticky-top">
      <div className="d-flex justify-content-between align-items-center p-3 p-lg-4">
        {/* Breadcrumb */}
        <div className="flex-grow-1">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0 small">
              <li className="breadcrumb-item">
                <Link to="/" className="text-decoration-none">
                  Dashboard
                </Link>
              </li>
              {location.pathname !== "/" && (
                <li className="breadcrumb-item active" aria-current="page">
                  {getBreadcrumb()}
                </li>
              )}
            </ol>
          </nav>
        </div>

        {/* User Info & Actions - Responsive */}
        <div className="d-flex align-items-center gap-2 gap-md-3">
          {/* User email - hide on mobile */}
          <div className="d-none d-md-block small text-muted">
            {user?.email}
          </div>

          {/* Logout button */}
          <button
            className="btn btn-sm btn-outline-danger"
            onClick={handleLogout}
            title="Logout"
          >
            <span className="d-none d-sm-inline">Logout</span>
            <span className="d-inline d-sm-none">↪️</span>
          </button>
        </div>
      </div>
    </header>
  );
}
