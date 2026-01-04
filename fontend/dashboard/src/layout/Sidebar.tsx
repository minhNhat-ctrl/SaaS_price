import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

/**
 * Sidebar Component
 * Collapsible mobile, fixed desktop
 * Navigation không re-render khi đổi page
 */

interface MenuItem {
  label: string;
  path: string;
  icon?: string;
}

const menuItems: MenuItem[] = [
  { label: "Dashboard", path: "/", icon: "📊" },
  { label: "Catalog", path: "/catalog", icon: "📚" },
  { label: "Products", path: "/products", icon: "📦" },
  { label: "Profile", path: "/profile", icon: "👤" },
];

export function Sidebar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle button */}
      <button
        className="d-lg-none btn btn-sm m-2 position-fixed"
        style={{ zIndex: 1001, bottom: "20px", right: "20px" }}
        onClick={() => setOpen(!open)}
        aria-label="Toggle menu"
      >
        ☰
      </button>

      {/* Sidebar */}
      <nav
        className={`bg-white border-end h-100 d-flex flex-column ${
          open ? "show" : "d-none d-lg-flex"
        }`}
        style={{ width: "250px", position: "fixed", left: 0, top: 0, zIndex: 1000 }}
      >
        {/* Logo */}
        <div className="p-3 fw-bold border-bottom" style={{ fontSize: "18px" }}>
          PriceSync
        </div>

        {/* Menu items */}
        <ul className="nav flex-column flex-grow-1 p-2">
          {menuItems.map((item) => (
            <li className="nav-item" key={item.path}>
              <Link
                to={item.path}
                className={`nav-link px-3 py-2 rounded ${
                  location.pathname === item.path
                    ? "bg-light text-primary fw-600"
                    : "text-dark"
                }`}
                onClick={() => setOpen(false)}
                style={{
                  borderLeft:
                    location.pathname === item.path ? "3px solid #0066cc" : "none",
                  paddingLeft: location.pathname === item.path ? "12px" : "15px",
                }}
              >
                {item.icon && <span className="me-2">{item.icon}</span>}
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* Mobile overlay */}
      {open && (
        <div
          className="d-lg-none position-fixed top-0 start-0 w-100 h-100"
          style={{
            backgroundColor: "rgba(0,0,0,0.5)",
            zIndex: 999,
          }}
          onClick={() => setOpen(false)}
        />
      )}
    </>
  );
}
