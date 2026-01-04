import { useState } from "react";

interface InlineEditorProps {
  id: string;
  initialValue: string | number;
  onSave: (id: string, value: string | number) => void | Promise<void>;
  loading?: boolean;
  type?: "text" | "number" | "email";
  className?: string;
}

/**
 * InlineEditor Component
 * Edit field directly trong bảng, không cần modal
 * 2 clicks: edit + save (instead of 5 modal clicks)
 */
export function InlineEditor({
  id,
  initialValue,
  onSave,
  loading = false,
  type = "text",
  className = "form-control form-control-sm",
}: InlineEditorProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initialValue);

  const handleSave = async () => {
    try {
      await onSave(id, value);
      setEditing(false);
    } catch (error) {
      console.error("Save failed:", error);
    }
  };

  const handleCancel = () => {
    setValue(initialValue);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="d-flex gap-1">
        <input
          type={type}
          className={className}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button
          className="btn btn-sm btn-success"
          onClick={handleSave}
          disabled={loading}
        >
          ✓
        </button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={handleCancel}
          disabled={loading}
        >
          ✕
        </button>
      </div>
    );
  }

  return (
    <div className="d-flex align-items-center gap-2">
      <span>{value}</span>
      <button
        className="btn btn-sm btn-link p-0 text-primary"
        onClick={() => setEditing(true)}
        style={{ textDecoration: "none" }}
      >
        ✏️
      </button>
    </div>
  );
}
