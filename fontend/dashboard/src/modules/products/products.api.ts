/**
 * Products Module API Client
 *
 * Nguyên tắc:
 * - Mỗi module tự quản lý API client
 * - API URL cố định (proxied qua Nginx)
 * - Không có global API router
 */

import type {
  Product,
  ProductURL,
  PriceRecord,
  CreateProductPayload,
  UpdateProductPayload,
  AddProductURLPayload,
  RecordPricePayload,
} from "./types";

// Helper function for API calls
async function apiCall<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
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

/**
 * List all products for a tenant
 */
export async function listProducts(tenantId: string): Promise<Product[]> {
  const data = await apiCall<{
    success: boolean;
    products?: Product[];
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/`);

  if (data.success && data.products) return data.products;
  throw new Error(data.error || "Failed to load products");
}

/**
 * Create a new product
 */
export async function createProduct(
  tenantId: string,
  payload: CreateProductPayload
): Promise<Product> {
  const data = await apiCall<{
    success: boolean;
    product?: Product;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (data.success && data.product) return data.product;
  throw new Error(data.error || "Failed to create product");
}

/**
 * Get a specific product
 */
export async function getProduct(
  tenantId: string,
  productId: string
): Promise<Product> {
  const data = await apiCall<{
    success: boolean;
    product?: Product;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/`);

  if (data.success && data.product) return data.product;
  throw new Error(data.error || "Failed to load product");
}

/**
 * Update a product
 */
export async function updateProduct(
  tenantId: string,
  productId: string,
  payload: UpdateProductPayload
): Promise<Product> {
  const data = await apiCall<{
    success: boolean;
    product?: Product;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (data.success && data.product) return data.product;
  throw new Error(data.error || "Failed to update product");
}

/**
 * Delete a product
 */
export async function deleteProduct(
  tenantId: string,
  productId: string
): Promise<void> {
  const data = await apiCall<{
    success: boolean;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/`, {
    method: "DELETE",
  });

  if (!data.success) {
    throw new Error(data.error || "Failed to delete product");
  }
}

/**
 * List product URLs (tracking links)
 */
export async function listProductURLs(
  tenantId: string,
  productId: string
): Promise<ProductURL[]> {
  const data = await apiCall<{
    success: boolean;
    urls?: ProductURL[];
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/urls/`);

  if (data.success && data.urls) return data.urls;
  throw new Error(data.error || "Failed to load product URLs");
}

/**
 * Add a new product URL (tracking link)
 */
export async function addProductURL(
  tenantId: string,
  productId: string,
  payload: AddProductURLPayload
): Promise<ProductURL> {
  const data = await apiCall<{
    success: boolean;
    url?: ProductURL;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/urls/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (data.success && data.url) return data.url;
  throw new Error(data.error || "Failed to add product URL");
}

/**
 * Update a product URL
 */
export async function updateProductURL(
  tenantId: string,
  productId: string,
  urlId: string,
  payload: Partial<AddProductURLPayload>
): Promise<ProductURL> {
  const data = await apiCall<{
    success: boolean;
    url?: ProductURL;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/urls/${urlId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (data.success && data.url) return data.url;
  throw new Error(data.error || "Failed to update product URL");
}

/**
 * Delete a product URL
 */
export async function deleteProductURL(
  tenantId: string,
  productId: string,
  urlId: string
): Promise<void> {
  const data = await apiCall<{
    success: boolean;
    error?: string;
  }>(`/api/products/tenants/${tenantId}/products/${productId}/urls/${urlId}/`, {
    method: "DELETE",
  });

  if (!data.success) {
    throw new Error(data.error || "Failed to delete product URL");
  }
}

/**
 * Record a price for a product URL
 */
export async function recordPrice(
  tenantId: string,
  productId: string,
  urlId: string,
  payload: RecordPricePayload
): Promise<PriceRecord> {
  const data = await apiCall<{
    success: boolean;
    price?: PriceRecord;
    error?: string;
  }>(
    `/api/products/tenants/${tenantId}/products/${productId}/urls/${urlId}/prices/`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );

  if (data.success && data.price) return data.price;
  throw new Error(data.error || "Failed to record price");
}

/**
 * Get price history for a product URL
 */
export async function getPriceHistory(
  tenantId: string,
  productId: string,
  urlId: string
): Promise<PriceRecord[]> {
  const data = await apiCall<{
    success: boolean;
    prices?: PriceRecord[];
    error?: string;
  }>(
    `/api/products/tenants/${tenantId}/products/${productId}/urls/${urlId}/prices/`
  );

  if (data.success && data.prices) return data.prices;
  throw new Error(data.error || "Failed to load price history");
}
