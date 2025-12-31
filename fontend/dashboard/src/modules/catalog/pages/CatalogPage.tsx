import { useState, useEffect } from "react";
import { fetchProducts, Product } from "../catalog.api";
import { ProductTable } from "../components/ProductTable";

/**
 * Catalog Page
 * 
 * Nguyên tắc:
 * - Page gọi API (không Layout)
 * - Fetch data khi component mount
 * - Tách widget nhỏ (ProductTable)
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
    return <div className="alert alert-info">Loading products...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <div className="catalog-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h1>Catalog</h1>
        <button
          className="btn btn-primary"
          style={{ borderRadius: "4px" }}
          disabled
          title="Coming soon"
        >
          + Add Product
        </button>
      </div>

      {products.length === 0 ? (
        <div className="alert alert-warning">No products found</div>
      ) : (
        <ProductTable products={products} />
      )}
    </div>
  );
}
