/**
 * Products Module Type Definitions
 *
 * Matched with backend API responses
 */

export interface Product {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  sku?: string;
  gtin?: string;
  status: "active" | "inactive";
  created_at?: string;
  updated_at?: string;
}

export interface ProductURL {
  id: string;
  product_id: string;
  url: string;
  marketplace?: string;
  is_primary: boolean;
  created_at?: string;
}

export interface PriceRecord {
  id: string;
  url_id: string;
  price: number;
  currency?: string;
  source?: string;
  recorded_at?: string;
}

export interface CreateProductPayload {
  name: string;
  description?: string;
  sku?: string;
  gtin?: string;
}

export interface UpdateProductPayload {
  name?: string;
  description?: string;
  sku?: string;
  gtin?: string;
  status?: "active" | "inactive";
}

export interface AddProductURLPayload {
  url: string;
  marketplace?: string;
  is_primary?: boolean;
}

export interface RecordPricePayload {
  price: number;
  currency?: string;
  source?: string;
}
