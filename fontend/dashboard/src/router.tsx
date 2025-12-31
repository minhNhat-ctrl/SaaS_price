import { Routes, Route, Navigate } from "react-router-dom";
import { MainLayout } from "./layout/MainLayout";
import { DashboardHomePage } from "./pages/DashboardHomePage";
import { CatalogPage } from "./modules/catalog/pages/CatalogPage";

/**
 * Router Configuration
 * 
 * Nguyên tắc: Manual routing, rõ ràng, dễ debug
 * - Không dùng dynamic import
 * - Mỗi route tương ứng 1 module backend
 * 
 * Checklist khi thêm module mới:
 * 1. Tạo services/module_name/ (backend)
 * 2. Thêm import route
 * 3. Thêm <Route /> entry
 * 4. Tạo fontend/dashboard/modules/module_name/ folder
 */

interface RouteConfig {
  path: string;
  element: React.ReactNode;
  module: string; // Tham chiếu module backend
  label: string;
}

export const routeRegistry: RouteConfig[] = [
  {
    path: "/",
    element: <DashboardHomePage />,
    module: "dashboard",
    label: "Dashboard",
  },
  {
    path: "/catalog",
    element: <CatalogPage />,
    module: "catalog",
    label: "Catalog",
  },
];

export function AppRouter() {
  return (
    <MainLayout>
      <Routes>
        {routeRegistry.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MainLayout>
  );
}
