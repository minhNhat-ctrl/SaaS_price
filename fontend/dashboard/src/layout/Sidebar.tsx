import { Link, useLocation } from "react-router-dom";

/**
 * Sidebar Component
 * Navigation không re-render khi đổi page
 */

interface MenuItem {
  label: string;
  path: string;
  icon?: string;
}

const menuItems: MenuItem[] = [
  {
    label: "Dashboard",
    path: "/",
    icon: "📊",
  },
  {
    label: "Profile",
    path: "/profile",
    icon: "👤",
  },
  {
    label: "Catalog",
    path: "/catalog",
    icon: "📦",
  },
  // Thêm menu khi có module mới
];

export function Sidebar() {
  const location = useLocation();

  return (
    <nav
      className="sidebar"
      style={{
        width: "250px",
        borderRight: "1px solid #e5e5e5",
        padding: "20px 0",
        height: "100vh",
        position: "fixed",
        left: 0,
        top: 0,
      }}
    >
      <div className="p-3 fw-bold" style={{ fontSize: "18px" }}>
        PriceSync
      </div>

      <ul className="nav flex-column" style={{ padding: "10px" }}>
        {menuItems.map((item) => (
          <li className="nav-item" key={item.path}>
            <Link
              to={item.path}
              className={`nav-link ${
                location.pathname === item.path ? "active" : ""
              }`}
              style={{
                color: location.pathname === item.path ? "#0066cc" : "#333",
                borderLeft:
                  location.pathname === item.path ? "3px solid #0066cc" : "none",
                paddingLeft: "17px",
                fontWeight:
                  location.pathname === item.path ? "600" : "normal",
              }}
            >
              {item.icon && <span style={{ marginRight: "8px" }}>{item.icon}</span>}
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
