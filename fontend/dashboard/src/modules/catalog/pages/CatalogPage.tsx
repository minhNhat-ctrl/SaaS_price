import { useState, useEffect } from "react";
import { fetchProducts, Product } from "../catalog.api";
import { ProductTable } from "../components/ProductTable";

/**
 * Catalog Page
 * 
 * Nguyên tắc:
 * - Page gọi API (không Layout)
 * - Fetch data khi component mount
 * - Responsive layout, inline CRUD
 */

export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchProducts();
        setProducts(data);
      } catch (err) {
        setError("Failed to load products");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadProducts();
  }, []);

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading products...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger alert-dismissible fade show">
        {error}
        <button
          type="button"
          className="btn-close"
          onClick={() => setError(null)}
        />
      </div>
    );
  }

  return (
    <div className="catalog-page">
      {/* Page Header */}
      <div className="mb-4">
        <h1 className="h3 fw-bold mb-1">Catalog</h1>
        <p className="text-muted small mb-0">Browse all available products</p>
      </div>

      {/* Products Table */}
      {products.length === 0 ? (
        <div className="alert alert-info">No products available in catalog</div>
      ) : (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-3 p-md-4">
            <p className="text-muted small mb-3">
              {products.length} product{products.length !== 1 ? "s" : ""} in catalog
            </p>
            <ProductTable products={products} />
          </div>
        </div>
      )}
    </div>
  );
}
