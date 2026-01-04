import { useState } from "react";

interface ExpandableRowProps {
  id: string;
  summary: React.ReactNode;
  details: React.ReactNode;
  actions?: React.ReactNode;
  onExpand?: (id: string, expanded: boolean) => void;
}

/**
 * ExpandableRow Component
 * Nhấp vào hàng để mở rộng chi tiết
 * Giảm popup/modal, hiển thị đầy đủ info
 */
export function ExpandableRow({
  id,
  summary,
  details,
  actions,
  onExpand,
}: ExpandableRowProps) {
  const [expanded, setExpanded] = useState(false);

  const toggleExpand = () => {
    const newExpanded = !expanded;
    setExpanded(newExpanded);
    onExpand?.(id, newExpanded);
  };

  return (
    <>
      {/* Summary row */}
      <tr
        className="cursor-pointer"
        onClick={toggleExpand}
        style={{ cursor: "pointer" }}
      >
        <td style={{ width: "40px" }} className="text-center">
          <span className="text-muted" style={{ fontSize: "0.875rem" }}>
            {expanded ? "▼" : "▶"}
          </span>
        </td>
        {/* Summary content */}
        <td colSpan={999}>{summary}</td>
      </tr>

      {/* Details row */}
      {expanded && (
        <tr className="table-light">
          <td colSpan={999}>
            <div className="p-3 p-md-4">
              <div className="row g-3 mb-3">
                {details}
              </div>
              {actions && (
                <div className="border-top pt-3">
                  <div className="d-flex flex-wrap gap-2">{actions}</div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
