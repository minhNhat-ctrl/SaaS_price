import { Product } from "../catalog.api";

/**
 * Product Table Component
 * 
 * Hiển thị danh sách products
 * - Không logic phức tạp
 * - Nhận props từ parent (Page)
 */

interface ProductTableProps {
  products: Product[];
}

export function ProductTable({ products }: ProductTableProps) {
  return (
    <div
      className="table-responsive"
      style={{
        border: "1px solid #e5e5e5",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <table
        className="table table-sm"
        style={{
          marginBottom: 0,
        }}
      >
        <thead style={{ backgroundColor: "#f8f9fa", borderBottom: "1px solid #e5e5e5" }}>
          <tr>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Name
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              SKU
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Price
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Quantity
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Created
            </th>
            <th style={{ padding: "12px 15px", fontWeight: "600", fontSize: "13px" }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr
              key={product.id}
              style={{ borderBottom: "1px solid #e5e5e5" }}
            >
              <td style={{ padding: "12px 15px" }}>{product.name}</td>
              <td style={{ padding: "12px 15px" }}>{product.sku}</td>
              <td style={{ padding: "12px 15px" }}>${product.price}</td>
              <td style={{ padding: "12px 15px" }}>{product.quantity}</td>
              <td style={{ padding: "12px 15px", fontSize: "13px", color: "#666" }}>
                {new Date(product.createdAt).toLocaleDateString()}
              </td>
              <td style={{ padding: "12px 15px" }}>
                <button
                  className="btn btn-sm btn-link"
                  style={{ padding: 0, textDecoration: "none" }}
                  disabled
                  title="Coming soon"
                >
                  Edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
