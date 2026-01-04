import { useState, useEffect } from "react";

/**
 * Dashboard Home Page
 * Trang chủ hiển thị tổng quan module
 * Responsive: 1 cột mobile, 2-4 cột desktop
 */

interface DashboardStats {
  totalProducts: number;
  totalOrders: number;
  totalRevenue: number;
  activeUsers: number;
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
}

/**
 * StatCard - Component tái sử dụng
 * Hiển thị thống kê dạng card nhẹ
 */
function StatCard({ title, value, subtitle }: StatCardProps) {
  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body p-3 p-md-4">
        <h6 className="card-title text-muted mb-2 fw-500">{title}</h6>
        <div className="h3 fw-bold mb-1">{value}</div>
        <small className="text-muted">{subtitle}</small>
      </div>
    </div>
  );
}

export function DashboardHomePage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalProducts: 0,
    totalOrders: 0,
    totalRevenue: 0,
    activeUsers: 0,
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch dashboard stats từ API (khi có endpoint)
    // TODO: Gọi API để lấy dữ liệu
    
    // Dữ liệu mẫu
    setTimeout(() => {
      setStats({
        totalProducts: 1250,
        totalOrders: 347,
        totalRevenue: 45820,
        activeUsers: 234,
      });
      setLoading(false);
    }, 500);
  }, []);

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: "400px" }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-home">
      {/* Header */}
      <div className="mb-4">
        <h1 className="h3 mb-1 fw-bold">Dashboard</h1>
        <p className="text-muted mb-0">Overview của toàn bộ module</p>
      </div>

      {/* Stats Grid - Responsive 1/2/4 cột */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-sm-6 col-lg-3">
          <StatCard
            title="Total Products"
            value={stats.totalProducts.toLocaleString()}
            subtitle="Items in catalog"
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <StatCard
            title="Total Orders"
            value={stats.totalOrders.toLocaleString()}
            subtitle="This month"
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <StatCard
            title="Total Revenue"
            value={`$${stats.totalRevenue.toLocaleString()}k`}
            subtitle="Last 30 days"
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <StatCard
            title="Active Users"
            value={stats.activeUsers.toLocaleString()}
            subtitle="Online now"
          />
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="card border-0 shadow-sm">
        <div className="card-body p-3 p-md-4">
          <h6 className="card-title fw-bold mb-3">Quick Access</h6>
          <div className="d-flex flex-wrap gap-2">
            <a href="/catalog" className="btn btn-sm btn-outline-primary">
              📚 View Catalog
            </a>
            <a href="/products" className="btn btn-sm btn-outline-primary">
              📦 Manage Products
            </a>
            <a href="/profile" className="btn btn-sm btn-outline-secondary">
              👤 Profile
            </a>
          </div>
        </div>
      </div>

      {/* Module Information */}
      <div className="row g-3 mt-3">
        <div className="col-12 col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-body p-3 p-md-4">
              <h6 className="card-title fw-bold mb-2">📊 System Overview</h6>
              <ul className="list-unstyled small mb-0">
                <li className="py-1">✓ Multi-tenant architecture</li>
                <li className="py-1">✓ Catalog management module</li>
                <li className="py-1">✓ Product management system</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="col-12 col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-body p-3 p-md-4">
              <h6 className="card-title fw-bold mb-2">🚀 Features</h6>
              <ul className="list-unstyled small mb-0">
                <li className="py-1">✓ Inline CRUD operations</li>
                <li className="py-1">✓ Responsive mobile design</li>
                <li className="py-1">✓ Real-time data sync</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
