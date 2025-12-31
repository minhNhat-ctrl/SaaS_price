import { useState, useEffect } from "react";

/**
 * Dashboard Home Page
 * Trang chủ hiển thị tổng quan
 */

interface DashboardStats {
  totalProducts: number;
  totalOrders: number;
  totalRevenue: number;
  activeUsers: number;
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
    return <div className="alert alert-info">Loading...</div>;
  }

  return (
    <div className="dashboard-home">
      <h1 className="mb-4">Dashboard</h1>

      <div className="row">
        {/* Total Products */}
        <div className="col-md-3 mb-3">
          <div
            className="card"
            style={{
              border: "1px solid #e5e5e5",
              borderRadius: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <div className="card-body p-4">
              <h6 className="card-title text-muted mb-2">Total Products</h6>
              <div style={{ fontSize: "32px", fontWeight: "600" }}>
                {stats.totalProducts}
              </div>
              <small className="text-muted">Items in catalog</small>
            </div>
          </div>
        </div>

        {/* Total Orders */}
        <div className="col-md-3 mb-3">
          <div
            className="card"
            style={{
              border: "1px solid #e5e5e5",
              borderRadius: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <div className="card-body p-4">
              <h6 className="card-title text-muted mb-2">Total Orders</h6>
              <div style={{ fontSize: "32px", fontWeight: "600" }}>
                {stats.totalOrders}
              </div>
              <small className="text-muted">This month</small>
            </div>
          </div>
        </div>

        {/* Total Revenue */}
        <div className="col-md-3 mb-3">
          <div
            className="card"
            style={{
              border: "1px solid #e5e5e5",
              borderRadius: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <div className="card-body p-4">
              <h6 className="card-title text-muted mb-2">Total Revenue</h6>
              <div style={{ fontSize: "32px", fontWeight: "600" }}>
                ${stats.totalRevenue}k
              </div>
              <small className="text-muted">Last 30 days</small>
            </div>
          </div>
        </div>

        {/* Active Users */}
        <div className="col-md-3 mb-3">
          <div
            className="card"
            style={{
              border: "1px solid #e5e5e5",
              borderRadius: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <div className="card-body p-4">
              <h6 className="card-title text-muted mb-2">Active Users</h6>
              <div style={{ fontSize: "32px", fontWeight: "600" }}>
                {stats.activeUsers}
              </div>
              <small className="text-muted">Online now</small>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="row mt-4">
        <div className="col-12">
          <div
            className="card"
            style={{
              border: "1px solid #e5e5e5",
              borderRadius: "6px",
            }}
          >
            <div className="card-body p-4">
              <h5 className="card-title">Quick Actions</h5>
              <div style={{ display: "flex", gap: "10px" }}>
                <a href="/catalog" className="btn btn-sm btn-outline-primary">
                  View Catalog
                </a>
                <button
                  className="btn btn-sm btn-outline-secondary"
                  disabled
                  title="Coming soon"
                >
                  Export Report
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
