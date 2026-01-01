/**
 * Tenants Module API Client
 *
 * Nguyên tắc:
 * - Mỗi module tự quản lý API client
 * - API URL cố định (proxied qua Nginx)
 * - Không có global API router
 */

export type TenantStatus = "active" | "suspended" | "deleted";

export interface TenantDomain {
  domain: string;
  is_primary: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  schema_name: string;
  status: TenantStatus;
  domains: TenantDomain[];
  created_at?: string;
  updated_at?: string;
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

export async function listTenants(status?: TenantStatus): Promise<Tenant[]> {
  const query = status ? `?status=${status}` : "";
  const data = await apiCall<{ success: boolean; tenants?: Tenant[]; error?: string }>(
    `/api/tenants/${query}`
  );
  if (data.success && data.tenants) return data.tenants;
  throw new Error(data.error || "Failed to load tenants");
}

export async function createTenant(input: {
  name: string;
  slug: string;
  domain: string;
}): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    "/api/tenants/",
    { method: "POST", body: JSON.stringify(input) }
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to create tenant");
}

export async function getTenant(id: string): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    `/api/tenants/${id}/`
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to fetch tenant");
}

export async function updateTenant(
  id: string,
  input: { name?: string; slug?: string }
): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    `/api/tenants/${id}/`,
    { method: "PATCH", body: JSON.stringify(input) }
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to update tenant");
}

export async function activateTenant(id: string): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    `/api/tenants/${id}/activate/`,
    { method: "POST", body: JSON.stringify({}) }
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to activate tenant");
}

export async function suspendTenant(id: string): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    `/api/tenants/${id}/suspend/`,
    { method: "POST", body: JSON.stringify({}) }
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to suspend tenant");
}

export async function deleteTenant(id: string): Promise<void> {
  const data = await apiCall<{ success: boolean; error?: string }>(
    `/api/tenants/${id}/`,
    { method: "DELETE" }
  );
  if (!data.success) throw new Error(data.error || "Failed to delete tenant");
}

export async function addDomain(
  id: string,
  input: { domain: string; is_primary?: boolean }
): Promise<Tenant> {
  const data = await apiCall<{ success: boolean; tenant?: Tenant; error?: string }>(
    `/api/tenants/${id}/add-domain/`,
    { method: "POST", body: JSON.stringify(input) }
  );
  if (data.success && data.tenant) return data.tenant;
  throw new Error(data.error || "Failed to add domain");
}
