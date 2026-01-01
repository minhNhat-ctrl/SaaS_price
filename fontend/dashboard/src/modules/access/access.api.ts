/**
 * Access Module API Client
 *
 * RBAC: Role-Based Access Control
 * - Memberships: Người dùng + Roles trong Tenant
 * - Roles: Custom roles per tenant
 * - Permissions: Action permissions liên kết roles
 */

export interface Membership {
  id: string;
  user_id: string;
  tenant_id: string;
  email: string;
  status: "active" | "pending" | "revoked";
  roles: Role[];
  created_at?: string;
  updated_at?: string;
}

export interface Role {
  id: string;
  name: string;
  slug: string;
  tenant_id?: string;
  permissions: Permission[];
  created_at?: string;
}

export interface Permission {
  id: string;
  name: string;
  slug: string;
}

// Helper function for API calls
async function apiCall<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// ============================================================
// MEMBERSHIPS API
// ============================================================

export async function listMemberships(tenantId: string): Promise<Membership[]> {
  const data = await apiCall<{ success: boolean; memberships?: Membership[]; error?: string }>(
    `/api/access/memberships/?tenant_id=${tenantId}`
  );
  if (data.success && data.memberships) return data.memberships;
  throw new Error(data.error || "Failed to load memberships");
}

export async function getMembership(id: string): Promise<Membership> {
  const data = await apiCall<{ success: boolean; membership?: Membership; error?: string }>(
    `/api/access/memberships/${id}/`
  );
  if (data.success && data.membership) return data.membership;
  throw new Error(data.error || "Failed to fetch membership");
}

export async function inviteMember(input: {
  tenant_id: string;
  email: string;
  role_slugs: string[];
}): Promise<Membership> {
  const data = await apiCall<{ success: boolean; membership?: Membership; error?: string }>(
    "/api/access/memberships/invite/",
    { method: "POST", body: JSON.stringify(input) }
  );
  if (data.success && data.membership) return data.membership;
  throw new Error(data.error || "Failed to invite member");
}

export async function activateMembership(id: string): Promise<Membership> {
  const data = await apiCall<{ success: boolean; membership?: Membership; error?: string }>(
    `/api/access/memberships/${id}/activate/`,
    { method: "POST", body: JSON.stringify({}) }
  );
  if (data.success && data.membership) return data.membership;
  throw new Error(data.error || "Failed to activate membership");
}

export async function revokeMembership(id: string): Promise<Membership> {
  const data = await apiCall<{ success: boolean; membership?: Membership; error?: string }>(
    `/api/access/memberships/${id}/revoke/`,
    { method: "POST", body: JSON.stringify({}) }
  );
  if (data.success && data.membership) return data.membership;
  throw new Error(data.error || "Failed to revoke membership");
}

export async function assignRolesToMember(
  id: string,
  roleIds: string[]
): Promise<Membership> {
  const data = await apiCall<{ success: boolean; membership?: Membership; error?: string }>(
    `/api/access/memberships/${id}/assign-roles/`,
    { method: "POST", body: JSON.stringify({ role_ids: roleIds }) }
  );
  if (data.success && data.membership) return data.membership;
  throw new Error(data.error || "Failed to assign roles");
}

// ============================================================
// ROLES API
// ============================================================

export async function listRoles(tenantId: string): Promise<Role[]> {
  const data = await apiCall<{ success: boolean; roles?: Role[]; error?: string }>(
    `/api/access/roles/?tenant_id=${tenantId}`
  );
  if (data.success && data.roles) return data.roles;
  throw new Error(data.error || "Failed to load roles");
}

export async function createRole(input: {
  tenant_id: string;
  name: string;
  slug: string;
  permission_ids: string[];
}): Promise<Role> {
  const data = await apiCall<{ success: boolean; role?: Role; error?: string }>(
    "/api/access/roles/create/",
    { method: "POST", body: JSON.stringify(input) }
  );
  if (data.success && data.role) return data.role;
  throw new Error(data.error || "Failed to create role");
}

// ============================================================
// PERMISSION CHECK
// ============================================================

export async function checkPermission(input: {
  tenant_id: string;
  user_id: string;
  permission: string;
}): Promise<boolean> {
  const data = await apiCall<{ success: boolean; has_permission?: boolean; error?: string }>(
    "/api/access/check-permission/",
    { method: "POST", body: JSON.stringify(input) }
  );
  if (data.success) return data.has_permission ?? false;
  throw new Error(data.error || "Failed to check permission");
}
