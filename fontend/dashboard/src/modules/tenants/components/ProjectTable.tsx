import { Tenant, TenantStatus } from "../tenants.api";

/**
 * ProjectTable Component
 *
 * Hiển thị danh sách projects (tenants)
 * - Không logic phức tạp
 * - Nhận props từ parent (Page)
 * - Bootstrap 5 + light theme
 */

interface ProjectTableProps {
  projects: Tenant[];
  onEdit?: (project: Tenant) => void;
  onDelete?: (id: string) => void;
  onActivate?: (id: string) => void;
  onSuspend?: (id: string) => void;
}

function getStatusBadge(status: TenantStatus) {
  const styles: Record<TenantStatus, { bg: string; text: string }> = {
    active: { bg: "#e8f5e9", text: "#2e7d32" },
    suspended: { bg: "#fff3e0", text: "#e65100" },
    deleted: { bg: "#f3e5f5", text: "#6a1b9a" },
  };

  const style = styles[status];
  return (
    <span
      style={{
        padding: "4px 10px",
        borderRadius: "4px",
        fontSize: "12px",
        fontWeight: "600",
        backgroundColor: style.bg,
        color: style.text,
      }}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export function ProjectTable({
  projects,
  onEdit,
  onDelete,
  onActivate,
  onSuspend,
}: ProjectTableProps) {
  return (
    <div
      className="table-responsive"
      style={{
        border: "1px solid #e5e5e5",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <table
        className="table table-sm"
        style={{
          marginBottom: 0,
        }}
      >
        <thead style={{ backgroundColor: "#f8f9fa", borderBottom: "1px solid #e5e5e5" }}>
          <tr>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Project Name
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Slug
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Schema
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Status
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Domains
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Created
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => (
            <tr key={project.id} style={{ borderBottom: "1px solid #e5e5e5" }}>
              <td style={{ padding: "12px 15px", fontWeight: "500" }}>{project.name}</td>
              <td style={{ padding: "12px 15px", fontSize: "13px", color: "#666" }}>
                {project.slug}
              </td>
              <td
                style={{
                  padding: "12px 15px",
                  fontSize: "12px",
                  color: "#999",
                  fontFamily: "monospace",
                }}
              >
                {project.schema_name}
              </td>
              <td style={{ padding: "12px 15px" }}>{getStatusBadge(project.status)}</td>
              <td style={{ padding: "12px 15px", fontSize: "13px" }}>
                {project.domains.length > 0
                  ? project.domains.map((d) => d.domain).join(", ")
                  : "-"}
              </td>
              <td style={{ padding: "12px 15px", fontSize: "13px", color: "#666" }}>
                {project.created_at
                  ? new Date(project.created_at).toLocaleDateString()
                  : "-"}
              </td>
              <td style={{ padding: "12px 15px" }}>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {project.status === "active" && onSuspend && (
                    <button
                      className="btn btn-sm"
                      style={{
                        padding: "4px 8px",
                        fontSize: "12px",
                        color: "#e65100",
                        border: "1px solid #e65100",
                        background: "transparent",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                      onClick={() => onSuspend(project.id)}
                    >
                      Suspend
                    </button>
                  )}
                  {project.status === "suspended" && onActivate && (
                    <button
                      className="btn btn-sm"
                      style={{
                        padding: "4px 8px",
                        fontSize: "12px",
                        color: "#2e7d32",
                        border: "1px solid #2e7d32",
                        background: "transparent",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                      onClick={() => onActivate(project.id)}
                    >
                      Activate
                    </button>
                  )}
                  {onEdit && (
                    <button
                      className="btn btn-sm"
                      style={{
                        padding: "4px 8px",
                        fontSize: "12px",
                        color: "#0066cc",
                        border: "1px solid #0066cc",
                        background: "transparent",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                      onClick={() => onEdit(project)}
                    >
                      Edit
                    </button>
                  )}
                  {onDelete && project.status !== "deleted" && (
                    <button
                      className="btn btn-sm"
                      style={{
                        padding: "4px 8px",
                        fontSize: "12px",
                        color: "#c62828",
                        border: "1px solid #c62828",
                        background: "transparent",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                      onClick={() => {
                        if (window.confirm("Delete this project? (soft delete)")) {
                          onDelete(project.id);
                        }
                      }}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
