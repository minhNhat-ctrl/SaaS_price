import { Membership } from "../access.api";

interface MembershipTableProps {
  members: Membership[];
  onEdit?: (member: Membership) => void;
  onRevoke?: (id: string) => void;
  onActivate?: (id: string) => void;
}

function getStatusBadge(status: string) {
  const styles: Record<string, { bg: string; text: string }> = {
    active: { bg: "#e8f5e9", text: "#2e7d32" },
    pending: { bg: "#fff3e0", text: "#e65100" },
    revoked: { bg: "#f3e5f5", text: "#6a1b9a" },
  };

  const style = styles[status] || { bg: "#f5f5f5", text: "#666" };
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

export function MembershipTable({ members, onEdit, onRevoke, onActivate }: MembershipTableProps) {
  return (
    <div
      className="table-responsive"
      style={{
        border: "1px solid #e5e5e5",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <table className="table table-sm" style={{ marginBottom: 0 }}>
        <thead style={{ backgroundColor: "#f8f9fa", borderBottom: "1px solid #e5e5e5" }}>
          <tr>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Email
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Status
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Roles
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Joined
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id} style={{ borderBottom: "1px solid #e5e5e5" }}>
              <td style={{ padding: "12px 15px" }}>{member.email}</td>
              <td style={{ padding: "12px 15px" }}>{getStatusBadge(member.status)}</td>
              <td style={{ padding: "12px 15px", fontSize: "13px" }}>
                {member.roles.length > 0
                  ? member.roles.map((r) => r.name).join(", ")
                  : "No roles"}
              </td>
              <td style={{ padding: "12px 15px", fontSize: "13px", color: "#666" }}>
                {member.created_at
                  ? new Date(member.created_at).toLocaleDateString()
                  : "-"}
              </td>
              <td style={{ padding: "12px 15px" }}>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {member.status === "pending" && onActivate && (
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
                      onClick={() => onActivate(member.id)}
                    >
                      Accept
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
                      onClick={() => onEdit(member)}
                    >
                      Edit Roles
                    </button>
                  )}
                  {onRevoke && member.status !== "revoked" && (
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
                        if (window.confirm("Revoke access for this member?")) {
                          onRevoke(member.id);
                        }
                      }}
                    >
                      Revoke
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
