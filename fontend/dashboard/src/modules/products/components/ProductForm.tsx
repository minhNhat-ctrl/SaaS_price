import React from "react";
import type { Product, CreateProductPayload } from "../types";

interface ProductFormProps {
  show: boolean;
  onClose: () => void;
  onSubmit: (data: CreateProductPayload & { status?: string }) => Promise<void>;
  loading?: boolean;
  initialData?: Product;
  isEdit?: boolean;
}

export function ProductForm({
  show,
  onClose,
  onSubmit,
  loading,
  initialData,
  isEdit,
}: ProductFormProps) {
  const [formData, setFormData] = React.useState<CreateProductPayload & { status?: string }>({
    name: initialData?.name || "",
    description: initialData?.description || "",
    sku: initialData?.sku || "",
    gtin: initialData?.gtin || "",
    status: initialData?.status || "active",
  });

  React.useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name,
        description: initialData.description || "",
        sku: initialData.sku || "",
        gtin: initialData.gtin || "",
        status: initialData.status || "active",
      });
    } else {
      setFormData({
        name: "",
        description: "",
        sku: "",
        gtin: "",
        status: "active",
      });
    }
  }, [initialData, show]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      alert("Product name is required");
      return;
    }

    try {
      await onSubmit(formData);
      onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save product");
    }
  };

  if (!show) return null;

  return (
    <div
      className="modal d-block"
      style={{
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        display: show ? "block" : "none",
      }}
      onClick={onClose}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              {isEdit ? "Edit Product" : "Create New Product"}
            </h5>
            <button
              type="button"
              className="btn-close"
              onClick={onClose}
              disabled={loading}
            />
          </div>

          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label className="form-label">Product Name *</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  disabled={loading}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={formData.description || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  disabled={loading}
                  placeholder="Optional product description"
                />
              </div>

              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label">SKU</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.sku || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, sku: e.target.value })
                    }
                    disabled={loading}
                    placeholder="Stock Keeping Unit"
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label">GTIN</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.gtin || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, gtin: e.target.value })
                    }
                    disabled={loading}
                    placeholder="Global Trade Item Number"
                  />
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Status</label>
                <select
                  className="form-select"
                  value={formData.status || "active"}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value })
                  }
                  disabled={loading}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? "Saving..." : isEdit ? "Update Product" : "Create Product"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
