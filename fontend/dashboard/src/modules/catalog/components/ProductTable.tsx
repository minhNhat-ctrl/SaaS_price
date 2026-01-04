import { useState } from "react";
import { Product } from "../catalog.api";
import { DeleteAction, ExpandableRow } from "../../../shared/components";

/**
 * Product Table Component - Inline CRUD
 * 
 * UX tối ưu:
 * - Expandable row (chi tiết không popup)
 * - Inline edit (2 clicks thay vì 5)
 * - Delete + undo (không confirm modal)
 */

interface ProductTableProps {
  products: Product[];
  onUpdate?: (id: string, data: Partial<Product>) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
}

export function ProductTable({ products, onUpdate, onDelete }: ProductTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<Product>>({});
  const [loading, setLoading] = useState<string | null>(null);

  const handleEdit = (product: Product) => {
    setEditingId(product.id);
    setEditData(product);
  };

  const handleSave = async () => {
    if (!editingId || !onUpdate) return;

    try {
      setLoading(editingId);
      await onUpdate(editingId, editData);
      setEditingId(null);
    } finally {
      setLoading(null);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditData({});
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
            <th className="d-none d-lg-table-cell">Price</th>
            <th className="d-none d-lg-table-cell">Qty</th>
            <th style={{ width: "100px" }}>Actions</th>
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
                    {editingId === product.id && (
                      <div className="mt-2">
                        <div className="mb-2">
                          <input
                            type="text"
                            className="form-control form-control-sm"
                            placeholder="Name"
                            value={editData.name || ""}
                            onChange={(e) =>
                              setEditData({ ...editData, name: e.target.value })
                            }
                          />
                        </div>
                        <div className="mb-2">
                          <input
                            type="text"
                            className="form-control form-control-sm"
                            placeholder="SKU"
                            value={editData.sku || ""}
                            onChange={(e) =>
                              setEditData({ ...editData, sku: e.target.value })
                            }
                          />
                        </div>
                        <div className="d-flex gap-1">
                          <button
                            className="btn btn-sm btn-success"
                            onClick={handleSave}
                            disabled={loading === product.id}
                          >
                            Save
                          </button>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={handleCancel}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="d-none d-md-block small text-muted">{product.sku}</div>
                  <div className="d-none d-lg-block small text-muted">${product.price}</div>
                </div>
              }
              details={
                <>
                  <div className="col-12 col-md-6">
                    <strong className="d-block text-muted mb-2">📋 Details</strong>
                    <div className="small">
                      <div className="mb-2">
                        <span className="text-muted">SKU:</span> {product.sku}
                      </div>
                      <div className="mb-2">
                        <span className="text-muted">Price:</span> ${product.price}
                      </div>
                      <div className="mb-2">
                        <span className="text-muted">Quantity:</span> {product.quantity}{" "}
                        units
                      </div>
                    </div>
                  </div>
                  <div className="col-12 col-md-6">
                    <strong className="d-block text-muted mb-2">📅 Metadata</strong>
                    <div className="small">
                      <div className="mb-2">
                        <span className="text-muted">Created:</span>{" "}
                        {new Date(product.createdAt).toLocaleDateString()}
                      </div>
                      <div>
                        <span className="text-muted">ID:</span> {product.id}
                      </div>
                    </div>
                  </div>
                </>
              }
              actions={
                <>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => handleEdit(product)}
                    disabled={editingId === product.id || loading === product.id}
                  >
                    ✏️ Edit
                  </button>
                  {onDelete && (
                    <DeleteAction
                      id={product.id}
                      onDelete={onDelete}
                      loading={loading === product.id}
                    />
                  )}
                </>
              }
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
