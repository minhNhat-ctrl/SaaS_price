import { useState, useEffect } from "react";
import {
  listMemberships,
  Membership,
  activateMembership,
  revokeMembership,
  inviteMember,
} from "../access.api";
import { MembershipTable } from "../components/MembershipTable";
import { listTenants, Tenant } from "../../tenants/tenants.api";

/**
 * Members Page (Project Members Management)
 *
 * Shows members for selected tenant/project
 */

export function MembersPage() {
  const [members, setMembers] = useState<Membership[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invite modal state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRoleSlugs, setInviteRoleSlugs] = useState<string[]>(["member"]);

  // Load tenants on mount
  useEffect(() => {
    const loadTenants = async () => {
      try {
        const data = await listTenants("active");
        setTenants(data);
        if (data.length > 0) {
          setSelectedTenantId(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load tenants:", err);
      }
    };
    loadTenants();
  }, []);

  const loadMembers = async () => {
    if (!selectedTenantId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await listMemberships(selectedTenantId);
      setMembers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTenantId) {
      loadMembers();
    }
  }, [selectedTenantId]);

  const handleActivate = async (id: string) => {
    try {
      const updated = await activateMembership(id);
      setMembers((prev) =>
        prev.map((m) => (m.id === id ? updated : m))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to activate member");
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      const updated = await revokeMembership(id);
      setMembers((prev) =>
        prev.map((m) => (m.id === id ? updated : m))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to revoke member");
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail || !selectedTenantId) {
      alert("Please enter an email address");
      return;
    }
    try {
      setInviteLoading(true);
      const newMember = await inviteMember({
        tenant_id: selectedTenantId,
        email: inviteEmail,
        role_slugs: inviteRoleSlugs,
      });
      setMembers((prev) => [...prev, newMember]);
      setShowInviteModal(false);
      setInviteEmail("");
      setInviteRoleSlugs(["member"]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to invite member");
    } finally {
      setInviteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="alert alert-info" role="status">
        Loading members...
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        {error}
        <button className="btn btn-sm btn-outline-danger ms-2" onClick={loadMembers}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="members-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h1 style={{ marginBottom: 0 }}>Team Members</h1>
        <button
          className="btn btn-primary"
          style={{ borderRadius: "4px" }}
          title="Invite new member"
          onClick={() => setShowInviteModal(true)}
        >
          + Invite Member
        </button>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
          onClick={() => setShowInviteModal(false)}
        >
          <div
            className="modal-dialog modal-dialog-centered"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Invite Team Member</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowInviteModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label">Email Address *</label>
                  <input
                    type="email"
                    className="form-control"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@example.com"
                    required
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Role</label>
                  <select
                    className="form-select"
                    value={inviteRoleSlugs[0]}
                    onChange={(e) => setInviteRoleSlugs([e.target.value])}
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
                <div className="mb-3">
                  <label className="form-label">Project</label>
                  <input
                    type="text"
                    className="form-control"
                    value={tenants.find((t) => t.id === selectedTenantId)?.name || ""}
                    disabled
                  />
                  <small className="text-muted">
                    Member will be invited to the currently selected project
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowInviteModal(false)}
                  disabled={inviteLoading}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleInvite}
                  disabled={inviteLoading || !inviteEmail}
                >
                  {inviteLoading ? "Inviting..." : "Send Invite"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Project Selector */}
      <div style={{ marginBottom: "16px" }}>
        <label style={{ marginRight: "8px", fontWeight: 500 }}>Project:</label>
        <select
          className="form-select"
          style={{ display: "inline-block", width: "auto", minWidth: "200px" }}
          value={selectedTenantId}
          onChange={(e) => setSelectedTenantId(e.target.value)}
        >
          {tenants.length === 0 && <option value="">No projects available</option>}
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: "16px", fontSize: "13px", color: "#666" }}>
        {members.length} member{members.length !== 1 ? "s" : ""}
      </div>

      {members.length === 0 ? (
        <div className="alert alert-info" role="status">
          No team members yet. Invite someone to collaborate.
        </div>
      ) : (
        <MembershipTable
          members={members}
          onActivate={handleActivate}
          onRevoke={handleRevoke}
        />
      )}
    </div>
  );
}
