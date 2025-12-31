/**
 * Authentication utilities
 * Quản lý token, session
 */

export const AUTH_TOKEN_KEY = "auth_token";
export const TENANT_KEY = "tenant_id";

export function setAuthToken(token: string) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getAuthToken() !== null;
}

export function setTenant(tenantId: string) {
  localStorage.setItem(TENANT_KEY, tenantId);
}

export function getTenant(): string | null {
  return localStorage.getItem(TENANT_KEY);
}

export function logout() {
  clearAuthToken();
  localStorage.removeItem(TENANT_KEY);
  window.location.href = "/login";
}
