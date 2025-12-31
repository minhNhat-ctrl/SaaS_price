import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

/**
 * MainLayout Component
 * Layout cố định, không re-render khi đổi page
 * Sidebar + Header + Content area
 */

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div
      className="main-layout"
      style={{
        display: "flex",
        minHeight: "100vh",
        backgroundColor: "#f8f9fa",
      }}
    >
      <Sidebar />

      <div
        className="content-wrapper"
        style={{
          marginLeft: "250px",
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Header />

        <main
          className="content"
          style={{
            flex: 1,
            padding: "20px",
            overflowY: "auto",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
