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
 * - Radio button thay dropdown cho tenant selector
 * - Responsive layout
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setShowForm(false);
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
      setShowForm(false);
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
      {/* Page Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-start align-md-items-center gap-3 mb-4">
        <div>
          <h1 className="h3 fw-bold mb-1">Products</h1>
          <p className="text-muted small mb-0">Manage all products for selected project</p>
        </div>
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

      {/* Project Selector - Visible tabs instead of dropdown */}
      <div className="card border-0 shadow-sm mb-4">
        <div className="card-body p-3 p-md-4">
          <h6 className="card-title fw-bold mb-3">📁 Select Project</h6>
          {tenants.length === 0 ? (
            <div className="alert alert-info mb-0">No projects available</div>
          ) : (
            <div className="d-flex flex-wrap gap-2">
              {tenants.map((tenant) => (
                <button
                  key={tenant.id}
                  className={`btn btn-sm ${
                    selectedTenantId === tenant.id
                      ? "btn-primary"
                      : "btn-outline-secondary"
                  }`}
                  onClick={() => setSelectedTenantId(tenant.id)}
                >
                  {tenant.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error Alert */}
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

      {/* Loading State */}
      {loading ? (
        <div className="d-flex justify-content-center align-items-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading products...</span>
          </div>
        </div>
      ) : (
        /* Products Table */
        <div className="card border-0 shadow-sm">
          <div className="card-body p-3 p-md-4">
            {products.length > 0 && (
              <h6 className="text-muted small mb-3">
                {products.length} product{products.length !== 1 ? "s" : ""}
              </h6>
            )}
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

      {/* Product Form Modal */}
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

      {/* URLs Modal */}
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
