import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

/**
 * MainLayout Component
 * Layout cố định, không re-render khi đổi page
 * Mobile-first responsive: stacked mobile, sidebar left desktop
 */

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="d-flex flex-column" style={{ minHeight: "100vh", backgroundColor: "#f8f9fa" }}>
      {/* Sidebar - fixed desktop, collapsible mobile */}
      <div className="position-fixed top-0 start-0" style={{ height: "100vh", zIndex: 1000, width: "250px" }}>
        <Sidebar />
      </div>

      {/* Content wrapper */}
      <div className="flex-grow-1" style={{ marginLeft: "250px" }}>
        {/* Header */}
        <Header />

        {/* Main content */}
        <main className="p-3 p-lg-4" style={{ overflowY: "auto" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
