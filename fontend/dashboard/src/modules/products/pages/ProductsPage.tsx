import { useState, useEffect } from "react";
import {
  listProducts,
  createProduct,
  deleteProduct,
  updateProduct,
} from "../products.api";
import { listTenants, Tenant } from "../../tenants/tenants.api";
import type { Product, CreateProductPayload } from "../types";
import { ProductTable } from "../components/ProductTable";
import { ProductForm } from "../components/ProductForm";
import { URLsModal } from "../components/URLsModal";

/**
 * Products Page
 *
 * Nguyên tắc:
 * - Page gọi API (không Layout)
 * - Fetch data khi component mount
 * - Tách widget nhỏ (ProductTable, ProductForm)
 * - Cho phép chọn project (tenant)
 */

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Create product modal state
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  // URLs modal state
  const [showURLsModal, setShowURLsModal] = useState(false);
  const [selectedProductForURLs, setSelectedProductForURLs] = useState<Product | null>(null);

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

  const loadProducts = async () => {
    if (!selectedTenantId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await listProducts(selectedTenantId);
      setProducts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, [selectedTenantId]); // Reload when tenant changes

  const handleCreate = async (formData: CreateProductPayload) => {
    if (!selectedTenantId) {
      alert("Please select a project");
      return;
    }

    try {
      setFormLoading(true);
      const created = await createProduct(selectedTenantId, formData);
      setProducts((prev) => [...prev, created]);
    } finally {
      setFormLoading(false);
    }
  };

  const handleUpdate = async (formData: CreateProductPayload & { status?: string }) => {
    if (!editingProduct || !selectedTenantId) return;

    try {
      setFormLoading(true);
      const updated = await updateProduct(selectedTenantId, editingProduct.id, {
        name: formData.name,
        description: formData.description,
        sku: formData.sku,
        gtin: formData.gtin,
        status: formData.status as "active" | "inactive",
      });
      setProducts((prev) =>
        prev.map((p) => (p.id === editingProduct.id ? updated : p))
      );
      setEditingProduct(null);
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (productId: string) => {
    if (!selectedTenantId) return;

    try {
      setActionLoading(productId);
      await deleteProduct(selectedTenantId, productId);
      setProducts((prev) => prev.filter((p) => p.id !== productId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete product");
    } finally {
      setActionLoading(null);
    }
  };

  const handleEdit = (product: Product) => {
    setEditingProduct(product);
    setShowForm(true);
  };

  const handleViewURLs = (product: Product) => {
    setSelectedProductForURLs(product);
    setShowURLsModal(true);
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Products</h1>
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingProduct(null);
            setShowForm(true);
          }}
        >
          + Add Product
        </button>
      </div>

      {/* Project Selector */}
      <div className="mb-4">
        <label className="form-label">Select Project</label>
        <select
          className="form-select"
          value={selectedTenantId}
          onChange={(e) => setSelectedTenantId(e.target.value)}
        >
          <option value="">-- Choose a project --</option>
          {tenants.map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible fade show">
          {error}
          <button
            type="button"
            className="btn-close"
            onClick={() => setError(null)}
          />
        </div>
      )}

      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading products...</span>
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm">
          <div className="card-body">
            <ProductTable
              products={products}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onViewURLs={handleViewURLs}
              actionLoading={actionLoading}
            />
          </div>
        </div>
      )}

      <ProductForm
        show={showForm}
        onClose={() => {
          setShowForm(false);
          setEditingProduct(null);
        }}
        onSubmit={editingProduct ? handleUpdate : handleCreate}
        loading={formLoading}
        initialData={editingProduct || undefined}
        isEdit={!!editingProduct}
      />

      {selectedProductForURLs && (
        <URLsModal
          show={showURLsModal}
          onClose={() => {
            setShowURLsModal(false);
            setSelectedProductForURLs(null);
          }}
          tenantId={selectedTenantId}
          productId={selectedProductForURLs.id}
          productName={selectedProductForURLs.name}
        />
      )}
    </div>
  );
}
