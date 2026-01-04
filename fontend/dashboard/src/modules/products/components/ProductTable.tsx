import { useState } from "react";
import type { Product } from "../types";
import { DeleteAction, ExpandableRow } from "../../../shared/components";

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
  const [editingId, setEditingId] = useState<string | null>(null);

  const handleEdit = (product: Product) => {
    setEditingId(product.id);
    onEdit(product);
  };

  if (products.length === 0) {
    return (
      <div className="text-center py-5 text-muted">
        <p>No products found</p>
      </div>
    );
  }

  return (
    <div className="table-responsive">
      <table className="table table-sm table-hover mb-0">
        <thead className="table-light">
          <tr>
            <th style={{ width: "40px" }}></th>
            <th>Product Name</th>
            <th className="d-none d-md-table-cell">SKU</th>
            <th className="d-none d-lg-table-cell">Status</th>
            <th style={{ width: "120px" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <ExpandableRow
              key={product.id}
              id={product.id}
              summary={
                <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div>
                    <strong>{product.name}</strong>
                    {product.description && (
                      <div className="small text-muted">{product.description}</div>
                    )}
                  </div>
                  <div className="d-none d-md-block small text-muted">{product.sku || "-"}</div>
                  <div className="d-none d-lg-block">
                    <span
                      className={`badge ${
                        product.status === "active" ? "bg-success" : "bg-secondary"
                      }`}
                    >
                      {product.status}
                    </span>
                  </div>
                </div>
              }
              details={
                <>
                  <div className="col-12 col-md-6">
                    <strong className="d-block text-muted mb-2">📋 Basic Info</strong>
                    <div className="small">
                      <div className="mb-2">
                        <span className="text-muted">SKU:</span> {product.sku || "-"}
                      </div>
                      <div className="mb-2">
                        <span className="text-muted">GTIN:</span> {product.gtin || "-"}
                      </div>
                      <div className="mb-2">
                        <span className="text-muted">Status:</span>
                        <div className="mt-1">
                          <div className="form-check form-check-inline">
                            <input
                              type="radio"
                              id={`status_active_${product.id}`}
                              name={`status_${product.id}`}
                              value="active"
                              checked={product.status === "active"}
                              disabled
                              readOnly
                            />
                            <label
                              htmlFor={`status_active_${product.id}`}
                              className="form-check-label"
                            >
                              Active
                            </label>
                          </div>
                          <div className="form-check form-check-inline">
                            <input
                              type="radio"
                              id={`status_inactive_${product.id}`}
                              name={`status_${product.id}`}
                              value="inactive"
                              checked={product.status === "inactive"}
                              disabled
                              readOnly
                            />
                            <label
                              htmlFor={`status_inactive_${product.id}`}
                              className="form-check-label"
                            >
                              Inactive
                            </label>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="col-12 col-md-6">
                    <strong className="d-block text-muted mb-2">📅 Metadata</strong>
                    <div className="small">
                      <div className="mb-2">
                        <span className="text-muted">Created:</span>{" "}
                        {product.created_at
                          ? new Date(product.created_at).toLocaleDateString()
                          : "-"}
                      </div>
                      <div className="mb-2">
                        <span className="text-muted">ID:</span> {product.id}
                      </div>
                    </div>
                  </div>
                </>
              }
              actions={
                <>
                  <button
                    className="btn btn-sm btn-outline-info"
                    onClick={() => onViewURLs(product)}
                    disabled={actionLoading === product.id}
                  >
                    🔗 View URLs
                  </button>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => handleEdit(product)}
                    disabled={actionLoading === product.id || editingId === product.id}
                  >
                    ✏️ Edit
                  </button>
                  <DeleteAction
                    id={product.id}
                    onDelete={onDelete}
                    loading={actionLoading === product.id}
                  />
                </>
              }
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
