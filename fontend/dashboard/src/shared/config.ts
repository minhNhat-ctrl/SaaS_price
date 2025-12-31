/**
 * Environment configuration
 */

export const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

export const APP_NAME = "PriceSync";
export const APP_VERSION = "0.1.0";

// API Endpoints
export const API_ENDPOINTS = {
  CATALOG: {
    PRODUCTS: "/api/catalog/products",
  },
  AUTH: {
    LOGIN: "/api/auth/login",
    LOGOUT: "/api/auth/logout",
    REFRESH: "/api/auth/refresh",
  },
};
