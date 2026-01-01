import { useState, useEffect } from "react";
import { listTenants, createTenant, Tenant, activateTenant, suspendTenant, deleteTenant } from "../tenants.api";
import { ProjectTable } from "../components/ProjectTable";

/**
 * Projects Page (Tenants List)
 *
 * Nguyên tắc:
 * - Page gọi API (không Layout)
 * - Fetch data khi component mount
 * - Tách widget nhỏ (ProjectTable)
 */

export function ProjectsPage() {
  const [projects, setProjects] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  // Create project modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newProject, setNewProject] = useState({ name: "", slug: "", domain: "" });

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      // Load only active projects by default
      const data = await listTenants("active");
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async () => {
    if (!newProject.name || !newProject.slug || !newProject.domain) {
      alert("Please fill in all fields");
      return;
    }
    try {
      setCreateLoading(true);
      const created = await createTenant(newProject);
      setProjects((prev) => [...prev, created]);
      setShowCreateModal(false);
      setNewProject({ name: "", slug: "", domain: "" });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleActivate = async (id: string) => {
    try {
      setActionLoading(id);
      const updated = await activateTenant(id);
      setProjects((prev) =>
        prev.map((p) => (p.id === id ? updated : p))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to activate project");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSuspend = async (id: string) => {
    try {
      setActionLoading(id);
      const updated = await suspendTenant(id);
      setProjects((prev) =>
        prev.map((p) => (p.id === id ? updated : p))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to suspend project");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      setActionLoading(id);
      await deleteTenant(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete project");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="alert alert-info" role="status">
        Loading projects...
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        {error}
        <button
          className="btn btn-sm btn-outline-danger ms-2"
          onClick={loadProjects}
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="projects-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h1 style={{ marginBottom: 0 }}>Projects</h1>
        <button
          className="btn btn-primary"
          style={{ borderRadius: "4px" }}
          title="Create new project"
          onClick={() => setShowCreateModal(true)}
        >
          + New Project
        </button>
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 1000
        }}>
          <div style={{
            backgroundColor: "white", padding: "24px", borderRadius: "8px",
            width: "400px", maxWidth: "90%"
          }}>
            <h3 style={{ marginBottom: "16px" }}>Create New Project</h3>
            <div style={{ marginBottom: "12px" }}>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}>
                Project Name
              </label>
              <input
                type="text"
                className="form-control"
                value={newProject.name}
                onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                placeholder="My Project"
              />
            </div>
            <div style={{ marginBottom: "12px" }}>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}>
                Slug (URL-friendly)
              </label>
              <input
                type="text"
                className="form-control"
                value={newProject.slug}
                onChange={(e) => setNewProject({ ...newProject, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
                placeholder="my-project"
              />
            </div>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}>
                Domain
              </label>
              <input
                type="text"
                className="form-control"
                value={newProject.domain}
                onChange={(e) => setNewProject({ ...newProject, domain: e.target.value })}
                placeholder="my-project.2kvietnam.com"
              />
            </div>
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowCreateModal(false)}
                disabled={createLoading}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreate}
                disabled={createLoading}
              >
                {createLoading ? "Creating..." : "Create Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: "16px", fontSize: "13px", color: "#666" }}>
        {projects.length} active project{projects.length !== 1 ? "s" : ""}
      </div>

      {projects.length === 0 ? (
        <div className="alert alert-warning" role="status">
          No active projects. Create one to get started.
        </div>
      ) : (
        <ProjectTable
          projects={projects}
          onActivate={handleActivate}
          onSuspend={handleSuspend}
          onDelete={handleDelete}
        />
      )}

      {actionLoading && (
        <div style={{ marginTop: "10px", fontSize: "12px", color: "#0066cc" }}>
          Processing...
        </div>
      )}
    </div>
  );
}
