import React from "react";
import {
  listProductURLs,
  addProductURL,
  updateProductURL,
  deleteProductURL,
  recordPrice,
  getPriceHistory,
} from "../products.api";
import type { ProductURL, PriceRecord, AddProductURLPayload } from "../types";

interface URLsModalProps {
  show: boolean;
  onClose: () => void;
  tenantId: string;
  productId: string;
  productName: string;
}

export function URLsModal({
  show,
  onClose,
  tenantId,
  productId,
  productName,
}: URLsModalProps) {
  const [urls, setUrls] = React.useState<ProductURL[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [showAddForm, setShowAddForm] = React.useState(false);
  const [formLoading, setFormLoading] = React.useState(false);

  // Form state
  const [newUrl, setNewUrl] = React.useState({
    url: "",
    marketplace: "",
    is_primary: false,
  });
  
  // Edit state
  const [editingUrlId, setEditingUrlId] = React.useState<string | null>(null);

  // Price history state
  const [selectedUrlId, setSelectedUrlId] = React.useState<string | null>(null);
  const [prices, setPrices] = React.useState<PriceRecord[]>([]);
  const [showPriceForm, setShowPriceForm] = React.useState(false);
  const [newPrice, setNewPrice] = React.useState({
    price: "",
    currency: "USD",
    source: "",
  });

  // Load URLs when modal opens
  React.useEffect(() => {
    if (show && productId && tenantId) {
      loadURLs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show, productId, tenantId]);

  const loadURLs = async () => {
    try {
      setLoading(true);
      const data = await listProductURLs(tenantId, productId);
      setUrls(data);
    } catch (err) {
      console.error("Failed to load URLs:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddURL = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newUrl.url.trim()) {
      alert("URL is required");
      return;
    }

    try {
      setFormLoading(true);
      const payload: AddProductURLPayload = {
        url: newUrl.url,
        marketplace: newUrl.marketplace || undefined,
        is_primary: newUrl.is_primary,
      };
      const added = await addProductURL(tenantId, productId, payload);
      setUrls((prev) => [...prev, added]);
      setNewUrl({ url: "", marketplace: "", is_primary: false });
      setShowAddForm(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add URL");
    } finally {
      setFormLoading(false);
    }
  };

  const handleLoadPrices = async (urlId: string) => {
    try {
      setLoading(true);
      const data = await getPriceHistory(tenantId, productId, urlId);
      setPrices(data);
      setSelectedUrlId(urlId);
    } catch (err) {
      console.error("Failed to load prices:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRecordPrice = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedUrlId || !newPrice.price) {
      alert("URL and price are required");
      return;
    }

    try {
      setFormLoading(true);
      await recordPrice(tenantId, productId, selectedUrlId, {
        price: parseFloat(newPrice.price),
        currency: newPrice.currency || undefined,
        source: newPrice.source || undefined,
      });
      // Reload prices
      await handleLoadPrices(selectedUrlId);
      setNewPrice({ price: "", currency: "USD", source: "" });
      setShowPriceForm(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to record price");
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditURL = (url: ProductURL) => {
    setEditingUrlId(url.id);
    setNewUrl({
      url: url.url,
      marketplace: url.marketplace || "",
      is_primary: url.is_primary,
    });
  };

  const handleUpdateURL = async () => {
    if (!editingUrlId || !newUrl.url.trim()) {
      alert("URL is required");
      return;
    }

    try {
      setFormLoading(true);
      const updated = await updateProductURL(tenantId, productId, editingUrlId, {
        url: newUrl.url,
        marketplace: newUrl.marketplace || undefined,
        is_primary: newUrl.is_primary,
      });
      setUrls((prev) =>
        prev.map((u) => (u.id === editingUrlId ? updated : u))
      );
      setEditingUrlId(null);
      setNewUrl({ url: "", marketplace: "", is_primary: false });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update URL");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteURL = async (urlId: string) => {
    if (!window.confirm("Delete this URL? This action cannot be undone.")) {
      return;
    }

    try {
      setFormLoading(true);
      await deleteProductURL(tenantId, productId, urlId);
      setUrls((prev) => prev.filter((u) => u.id !== urlId));
      if (selectedUrlId === urlId) {
        setSelectedUrlId(null);
        setPrices([]);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete URL");
    } finally {
      setFormLoading(false);
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
      <div
        className="modal-dialog modal-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              URLs & Prices - {productName}
            </h5>
            <button
              type="button"
              className="btn-close"
              onClick={onClose}
              disabled={loading}
            />
          </div>

          <div className="modal-body">
            {/* URLs Section */}
            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h6 className="mb-0">Tracking URLs</h6>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={() => setShowAddForm(!showAddForm)}
                >
                  + Add URL
                </button>
              </div>

              {showAddForm && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (editingUrlId) {
                      handleUpdateURL();
                    } else {
                      handleAddURL(e);
                    }
                  }}
                  className="mb-3 p-3 bg-light border rounded"
                >
                  <div className="mb-3">
                    <label className="form-label">URL *</label>
                    <input
                      type="url"
                      className="form-control"
                      value={newUrl.url}
                      onChange={(e) =>
                        setNewUrl({ ...newUrl, url: e.target.value })
                      }
                      disabled={formLoading}
                      placeholder="https://..."
                      required
                    />
                  </div>

                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label className="form-label">Marketplace</label>
                      <input
                        type="text"
                        className="form-control"
                        value={newUrl.marketplace}
                        onChange={(e) =>
                          setNewUrl({ ...newUrl, marketplace: e.target.value })
                        }
                        disabled={formLoading}
                        placeholder="e.g., Amazon, eBay"
                      />
                    </div>

                    <div className="col-md-6 mb-3">
                      <div className="form-check mt-4">
                        <input
                          type="checkbox"
                          className="form-check-input"
                          id="isPrimary"
                          checked={newUrl.is_primary}
                          onChange={(e) =>
                            setNewUrl({ ...newUrl, is_primary: e.target.checked })
                          }
                          disabled={formLoading}
                        />
                        <label className="form-check-label" htmlFor="isPrimary">
                          Primary URL
                        </label>
                      </div>
                    </div>
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      disabled={formLoading}
                    >
                      {formLoading
                        ? editingUrlId
                          ? "Updating..."
                          : "Adding..."
                        : editingUrlId
                        ? "Update URL"
                        : "Add URL"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => {
                        setShowAddForm(false);
                        setEditingUrlId(null);
                        setNewUrl({ url: "", marketplace: "", is_primary: false });
                      }}
                      disabled={formLoading}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}

              {loading ? (
                <div className="text-center py-3">
                  <div className="spinner-border spinner-border-sm" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </div>
              ) : urls.length === 0 ? (
                <div className="text-muted text-center py-3">
                  No tracking URLs added yet
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-sm table-hover border">
                    <thead className="table-light">
                      <tr>
                        <th>URL</th>
                        <th>Marketplace</th>
                        <th>Primary</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {urls.map((url) => (
                        <tr key={url.id}>
                          <td>
                            <a href={url.url} target="_blank" rel="noreferrer">
                              {url.url.length > 40
                                ? url.url.substring(0, 40) + "..."
                                : url.url}
                            </a>
                          </td>
                          <td>{url.marketplace || "-"}</td>
                          <td>
                            {url.is_primary && (
                              <span className="badge bg-success">Yes</span>
                            )}
                          </td>
                          <td>
                            <div className="btn-group" role="group">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-info"
                                onClick={() => handleLoadPrices(url.id)}
                                disabled={loading || formLoading}
                              >
                                Prices
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-warning"
                                onClick={() => handleEditURL(url)}
                                disabled={formLoading}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => handleDeleteURL(url.id)}
                                disabled={formLoading}
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Price History Section */}
            {selectedUrlId && (
              <div className="mb-0 p-3 bg-light border rounded">
                <h6 className="mb-3">Price History</h6>

                {showPriceForm && (
                  <form onSubmit={handleRecordPrice} className="mb-3 p-3 bg-white border rounded">
                    <div className="row">
                      <div className="col-md-6 mb-3">
                        <label className="form-label">Price *</label>
                        <input
                          type="number"
                          step="0.01"
                          className="form-control"
                          value={newPrice.price}
                          onChange={(e) =>
                            setNewPrice({ ...newPrice, price: e.target.value })
                          }
                          disabled={formLoading}
                          placeholder="0.00"
                          required
                        />
                      </div>

                      <div className="col-md-6 mb-3">
                        <label className="form-label">Currency</label>
                        <input
                          type="text"
                          className="form-control"
                          value={newPrice.currency}
                          onChange={(e) =>
                            setNewPrice({ ...newPrice, currency: e.target.value })
                          }
                          disabled={formLoading}
                          placeholder="USD"
                        />
                      </div>
                    </div>

                    <div className="mb-3">
                      <label className="form-label">Source</label>
                      <input
                        type="text"
                        className="form-control"
                        value={newPrice.source}
                        onChange={(e) =>
                          setNewPrice({ ...newPrice, source: e.target.value })
                        }
                        disabled={formLoading}
                        placeholder="e.g., Manual, API"
                      />
                    </div>

                    <div className="d-flex gap-2">
                      <button
                        type="submit"
                        className="btn btn-primary btn-sm"
                        disabled={formLoading}
                      >
                        {formLoading ? "Recording..." : "Record Price"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => setShowPriceForm(false)}
                        disabled={formLoading}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                <button
                  type="button"
                  className="btn btn-sm btn-outline-primary mb-3"
                  onClick={() => setShowPriceForm(!showPriceForm)}
                >
                  + Record New Price
                </button>

                {prices.length === 0 ? (
                  <div className="text-muted text-center py-3">
                    No price history yet
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm table-hover border">
                      <thead className="table-light">
                        <tr>
                          <th>Price</th>
                          <th>Currency</th>
                          <th>Source</th>
                          <th>Recorded At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {prices.map((price) => (
                          <tr key={price.id}>
                            <td className="fw-bold">{price.price}</td>
                            <td>{price.currency || "-"}</td>
                            <td>{price.source || "-"}</td>
                            <td>
                              {price.recorded_at
                                ? new Date(price.recorded_at).toLocaleDateString()
                                : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
