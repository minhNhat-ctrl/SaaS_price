import type { Product } from "../types";

interface ProductTableProps {
  products: Product[];
  onEdit: (product: Product) => void;
  onDelete: (productId: string) => void;
  onViewURLs: (product: Product) => void;
  actionLoading?: string | null;
}

export function ProductTable({
  products,
  onEdit,
  onDelete,
  onViewURLs,
  actionLoading,
}: ProductTableProps) {
  return (
    <div className="table-responsive">
      <table className="table table-hover border">
        <thead className="table-light">
          <tr>
            <th>Product Name</th>
            <th>SKU</th>
            <th>GTIN</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-4 text-muted">
                No products found
              </td>
            </tr>
          ) : (
            products.map((product) => (
              <tr key={product.id}>
                <td>
                  <strong>{product.name}</strong>
                  {product.description && (
                    <div style={{ fontSize: "0.875rem", color: "#666" }}>
                      {product.description}
                    </div>
                  )}
                </td>
                <td>{product.sku || "-"}</td>
                <td>{product.gtin || "-"}</td>
                <td>
                  <span
                    className={
                      product.status === "active"
                        ? "badge bg-success"
                        : "badge bg-secondary"
                    }
                  >
                    {product.status}
                  </span>
                </td>
                <td>
                  {product.created_at
                    ? new Date(product.created_at).toLocaleDateString()
                    : "-"}
                </td>
                <td>
                  <div className="btn-group" role="group">
                    <button
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => onViewURLs(product)}
                      disabled={actionLoading === product.id}
                    >
                      URLs
                    </button>
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => onEdit(product)}
                      disabled={actionLoading === product.id}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => {
                        const confirmed = window.confirm(
                          `Delete "${product.name}"? This action cannot be undone.`
                        );
                        if (confirmed) {
                          onDelete(product.id);
                        }
                      }}
                      disabled={actionLoading === product.id}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
