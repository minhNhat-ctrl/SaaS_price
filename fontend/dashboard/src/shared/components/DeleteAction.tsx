import { useState } from "react";

interface DeleteActionProps {
  id: string;
  onDelete: (id: string) => void;
  loading?: boolean;
  label?: string;
}

/**
 * DeleteAction Component
 * Hiển thị delete button với undo timer (5s)
 * Reduce: 1 click delete + undo (thay vì confirm modal)
 */
export function DeleteAction({ id, onDelete, loading = false, label = "Delete" }: DeleteActionProps) {
  const [deleted, setDeleted] = useState(false);
  const [undoTimer, setUndoTimer] = useState<NodeJS.Timeout | null>(null);

  const handleDelete = () => {
    setDeleted(true);
    const timer = setTimeout(() => {
      onDelete(id);
      setDeleted(false);
    }, 5000);
    setUndoTimer(timer);
  };

  const handleUndo = () => {
    if (undoTimer) {
      clearTimeout(undoTimer);
      setUndoTimer(null);
    }
    setDeleted(false);
  };

  if (deleted) {
    return (
      <div className="alert alert-warning alert-sm py-1 px-2 mb-0" style={{ fontSize: "0.875rem" }}>
        <span className="me-2">Deleting in 5s...</span>
        <button
          className="btn btn-sm btn-link p-0 text-warning"
          onClick={handleUndo}
          style={{ textDecoration: "none" }}
        >
          Undo
        </button>
      </div>
    );
  }

  return (
    <button
      className="btn btn-sm btn-link text-danger p-0"
      onClick={handleDelete}
      disabled={loading}
      style={{ textDecoration: "none" }}
    >
      {loading ? "..." : label}
    </button>
  );
}
