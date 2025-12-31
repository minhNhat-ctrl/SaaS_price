/**
 * Catalog Module - API Client
 * 
 * Nguyên tắc:
 * - Mỗi module tự quản lý API client
 * - API URL cố định, không sinh động
 * - Không có global API router
 */

import { api } from "../../shared/api";

export interface Product {
  id: string;
  name: string;
  sku: string;
  price: number;
  quantity: number;
  createdAt: string;
}

export interface CreateProductInput {
  name: string;
  sku: string;
  price: number;
  quantity: number;
}

/**
 * Fetch danh sách products
 */
export async function fetchProducts(): Promise<Product[]> {
  try {
    const response = await api.get<{ data: Product[] }>("/api/catalog/products");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch products:", error);
    throw error;
  }
}

/**
 * Fetch chi tiết 1 product
 */
export async function fetchProduct(id: string): Promise<Product> {
  try {
    const response = await api.get<{ data: Product }>(
      `/api/catalog/products/${id}`
    );
    return response.data;
  } catch (error) {
    console.error("Failed to fetch product:", error);
    throw error;
  }
}

/**
 * Tạo product mới
 */
export async function createProduct(input: CreateProductInput): Promise<Product> {
  try {
    const response = await api.post<{ data: Product }>(
      "/api/catalog/products",
      input
    );
    return response.data;
  } catch (error) {
    console.error("Failed to create product:", error);
    throw error;
  }
}

/**
 * Cập nhật product
 */
export async function updateProduct(
  id: string,
  input: Partial<CreateProductInput>
): Promise<Product> {
  try {
    const response = await api.put<{ data: Product }>(
      `/api/catalog/products/${id}`,
      input
    );
    return response.data;
  } catch (error) {
    console.error("Failed to update product:", error);
    throw error;
  }
}

/**
 * Xóa product
 */
export async function deleteProduct(id: string): Promise<void> {
  try {
    await api.delete(`/api/catalog/products/${id}`);
  } catch (error) {
    console.error("Failed to delete product:", error);
    throw error;
  }
}
