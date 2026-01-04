# Frontend Guidelines – SaaS Dashboard

## 1. Mục tiêu

Frontend của hệ thống SaaS được thiết kế theo các tiêu chí:

- Nhẹ, nhanh, ổn định
- Đơn giản, tối giản (minimal)
- Không màu mè, không hiệu ứng dư thừa
- Light theme mặc định
- Ưu tiên khả năng đọc code, maintain, mở rộng lâu dài
- Phù hợp kiến trúc module backend (Clean Architecture / DDD)

Frontend **không phải nơi chứa logic nghiệp vụ**, mà chỉ:
- Gọi API
- Hiển thị dữ liệu
- Điều hướng người dùng

---

## 2. Nền tảng UI sử dụng

### 2.1 Công nghệ chính

- **React** (Function Component)
- **Bootstrap 5 – CSS only**
- **React Router**
- **Fetch / Axios**

❌ Không sử dụng:
- Bootstrap JS (dropdown, modal bằng JS)
- jQuery
- UI framework nặng (AntD, MUI, Metronic…)
- CSS-in-JS
- Animation library

---

## 3. Nguyên tắc UI / UX

### 3.1 Phong cách

- Light theme
- Nền trắng / xám rất nhạt
- Border nhẹ, shadow nhẹ hoặc không shadow
- Typography rõ ràng, dễ đọc
- Spacing đều, không chật

### 3.2 Không sử dụng

- Gradient
- Neon / glow
- Animation phức tạp
- Icon quá nhiều
- Hiệu ứng hover cầu kỳ

---

## 4. Bootstrap – Quy ước sử dụng

Bootstrap **chỉ dùng cho layout & utility**, không dùng như UI framework hoàn chỉnh.

### 4.1 Được phép dùng

- Grid: `row`, `col-*`
- Spacing: `p-*`, `m-*`
- Typography: `fw-*`, `text-*`
- Card
- Border utilities

### 4.2 Không khuyến khích

- Component JS của Bootstrap
- Class quá dài, lồng nhiều cấp
- Ghi đè CSS phức tạp

---

## 5. Kiến trúc frontend

### 5.1 Cấu trúc thư mục tổng thể

```text
frontend/
└── dashboard/
    ├── app.tsx
    ├── router.tsx
    ├── layout/
    │   ├── MainLayout.tsx
    │   └── Sidebar.tsx
    ├── shared/
    │   ├── api.ts
    │   └── auth.ts
    └── modules/
        ├── catalog/
        ├── inventory/
        └── billing/
```
---
## 5.5 Module Registry (Frontend)

Mặc dù Backend có **auto-load via AdminModuleLoader**, 
Frontend **KHÔNG dùng dynamic import** vì:

✅ **Lý do dùng Manual Registry:**
1. Code rõ ràng, dễ debug
2. Dev biết chính xác page nào được enable
3. Không phụ thuộc React lazy loading
4. Build time tối ưu (tree-shaking tốt)

⚠️ **Cách thêm module frontend:**
  ```typescript
  // fontend/dashboard/router.tsx
  const routes = [
    {
      path: "/catalog",
      element: <CatalogPage />,
      module: "catalog"  // Tham khảo module backend tương ứng
    },
    {
      path: "/inventory",
      element: <InventoryPage />,
      module: "inventory"
    },
    // Thêm route mới khi có module backend mới
  ];
  ```

**Checklist khi thêm module:**
- [ ] Tạo `services/module_name/` (backend)
- [ ] Thêm route vào `router.tsx` (frontend)
- [ ] Tạo `fontend/dashboard/modules/module_name/` folder
- [ ] Viết API client `module_name.api.ts`
- [ ] Viết page component `pages/ModulePage.tsx`

Việc manual này **đảm bảo không có dead code** và **dễ refactor**.
**Không cần dynamic import, không cần registry hook.**


## 6. Giao tiếp API (Manual routing)

### 6.1 Nguyên tắc
- API URL **cố định, không sinh động**
- Mỗi module tự quản lý API client
- Không có global API router

### 6.2 Ví dụ

```typescript
// modules/catalog/catalog.api.ts
import { api } from "../../shared/api";

export const fetchProducts = () => {
  return api.get("/api/catalog/products");
};

export const createProduct = (data) => {
  return api.post("/api/catalog/products", data);
};
```

```typescript
// modules/catalog/pages/CatalogPage.tsx
import { fetchProducts } from "../catalog.api";

export function CatalogPage() {
  const [products, setProducts] = useState([]);
  
  useEffect(() => {
    fetchProducts().then(res => setProducts(res.data));
  }, []);
  
  return <ProductTable products={products} />;
}
```

---

## 7. Layout & Component

### 7.1 Layout cố định
- Sidebar không re-render khi đổi page
- Header hiển thị thông tin tenant
- Breadcrumb (tuỳ chọn)

### 7.2 Component structure
```typescript
// ❌ Sai
<LayoutWithApiCall />  // Layout gọi API

// ✅ Đúng
<Layout>
  <Page>  {/* Page gọi API */}
    <Table />
  </Page>
</Layout>
```

---

## 8. Hiệu năng

### 8.1 Bắt buộc
- ❌ Không fetch API dư thừa
- ❌ Không global state cho business data
- ❌ Không re-render layout khi data thay đổi

### 8.2 Ưu tiên
- Fetch data khi component mount
- Memo non-primitive props
- Tách widget nhỏ

---

## 9. Hiệu Lực

Cập nhật: **31 Dec 2025**
- ✅ React + Bootstrap CSS only
- ✅ Manual API routing (không dynamic)
- ✅ Manual module registry (rõ ràng)
- ✅ Tối giản, dễ maintain 2 năm

---

## 10. Thiết kế Responsive & Mobile-First

### 10.1 Nguyên tắc cơ bản

- **Mobile-first approach**: Thiết kế cho mobile trước, scale up cho desktop
- **Fluid layout**: Sử dụng `%`, `rem`, không fixed width
- **Touch-friendly**: Button tối thiểu 44x44px, spacing cho cảm ứng
- **Readable**: Font size >= 14px trên mobile, >= 16px desktop

### 10.2 Breakpoints (Bootstrap default)

```css
/* Mobile: < 576px (default) */
/* Tablet: >= 576px (sm) */
/* Desktop: >= 992px (lg) */
/* Large: >= 1200px (xl) */
```

**Chiến lược:**
- Stacked layout mobile (1 cột)
- 2-3 cột tablet (sm, md)
- 3-4 cột desktop (lg, xl)

---

## 11. Giảm Popup & Modal – Inline First

### 11.1 Nguyên tắc "Ít Popup"

❌ **KHÔNG dùng:**
- Modal xác nhận delete (5 thao tác)
- Dropdown select chỉ chứa 3 mục
- Toast quá nhiều

✅ **THAY THẾ:**
- Inline form (chỉnh sửa không rời khỏi bảng)
- Expand row (chi tiết trong hàng bảng)
- Inline delete + undo (1 click)

### 11.2 Ví dụ: Inline CRUD

```typescript
// modules/catalog/components/ProductTable.tsx
import { useState } from "react";

export function ProductTable({ products, onUpdate, onDelete }) {
  const [editId, setEditId] = useState(null);
  const [editData, setEditData] = useState({});

  return (
    <div className="table-responsive">
      <table className="table table-sm table-hover">
        <thead className="table-light">
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Stock</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              {editId === p.id ? (
                <>
                  <td>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={editData.name}
                      onChange={(e) =>
                        setEditData({ ...editData, name: e.target.value })
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      className="form-control form-control-sm"
                      value={editData.price}
                      onChange={(e) =>
                        setEditData({ ...editData, price: e.target.value })
                      }
                    />
                  </td>
                  <td colSpan="3">
                    <button
                      className="btn btn-sm btn-success me-2"
                      onClick={() => {
                        onUpdate(p.id, editData);
                        setEditId(null);
                      }}
                    >
                      Save
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => setEditId(null)}
                    >
                      Cancel
                    </button>
                  </td>
                </>
              ) : (
                <>
                  <td>{p.name}</td>
                  <td>${p.price}</td>
                  <td>{p.stock}</td>
                  <td>
                    <span
                      className={`badge ${
                        p.status === "active"
                          ? "bg-success"
                          : "bg-secondary"
                      }`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="text-end">
                    <button
                      className="btn btn-sm btn-link text-primary"
                      onClick={() => {
                        setEditId(p.id);
                        setEditData(p);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-sm btn-link text-danger"
                      onClick={() => onDelete(p.id)}
                    >
                      Delete
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Ưu điểm:**
- 2 click edit + save (thay vì 5 click modal)
- Dữ liệu không mất focus
- Mobile: scroll ngang bảng

---

## 12. Hiển thị Đầy Đủ Thông Tin – Không Dropdown

### 12.1 Nguyên tắc "Flat & Visible"

❌ **KHÔNG:**
```html
<select>
  <option>---</option>
  <option>Active</option>
</select>
```

✅ **THAY THẾ:**
```html
<!-- Radio buttons (nếu 2-3 mục) -->
<div className="btn-group" role="group">
  <input type="radio" name="status" value="active" />
  <label>Active</label>
  
  <input type="radio" name="status" value="inactive" />
  <label>Inactive</label>
</div>

<!-- Hoặc Toggle switch -->
<div className="form-check form-switch">
  <input className="form-check-input" type="checkbox" />
  <label>Enabled</label>
</div>
```

### 12.2 Ví dụ: Expandable Row (Chi tiết không cần modal)

```typescript
// modules/catalog/components/ExpandableProductRow.tsx
import { useState } from "react";

export function ExpandableProductRow({ product, onUpdate }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <td>
          <span className={`${expanded ? "▼" : "▶"}`}></span>
          {product.name}
        </td>
        <td>${product.price}</td>
        <td>{product.stock} units</td>
        <td>
          <span className={`badge bg-${product.status === 'active' ? 'success' : 'secondary'}`}>
            {product.status}
          </span>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-light">
          <td colSpan="4">
            <div className="p-3">
              <div className="row g-3">
                <div className="col-md-6">
                  <strong>Description:</strong>
                  <p>{product.description}</p>
                </div>
                <div className="col-md-6">
                  <strong>Category:</strong>
                  <p>{product.category}</p>
                  <strong>SKU:</strong>
                  <p>{product.sku}</p>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
```

---

## 13. CRUD Tối Giản – Ít Thao Tác Nhất

### 13.1 Chiến lược "1-Click Action"

| Action | Cách tối ưu | Thao tác |
|--------|-------------|---------|
| Create | Form inline + Save (hover) | 2 click |
| Read | Bảng + Expand row | 1 click |
| Update | Edit inline trong hàng | 2 click |
| Delete | 1-click + Undo (5 giây) | 1 click |

### 13.2 Ví dụ: Delete với Undo

```typescript
// modules/catalog/components/DeleteAction.tsx
export function DeleteAction({ id, onDelete }) {
  const [deleted, setDeleted] = useState(false);
  const [undoTimer, setUndoTimer] = useState(null);

  const handleDelete = () => {
    setDeleted(true);
    const timer = setTimeout(() => {
      onDelete(id);
      setDeleted(false);
    }, 5000);
    setUndoTimer(timer);
  };

  const handleUndo = () => {
    clearTimeout(undoTimer);
    setDeleted(false);
  };

  if (deleted) {
    return (
      <div className="alert alert-warning alert-sm m-0">
        Deleting in 5s...
        <button
          className="btn btn-sm btn-link ms-2"
          onClick={handleUndo}
        >
          Undo
        </button>
      </div>
    );
  }

  return (
    <button
      className="btn btn-sm btn-link text-danger"
      onClick={handleDelete}
    >
      Delete
    </button>
  );
}
```

---

## 14. Layout Responsive – Desktop & Mobile

### 14.1 Sidebar Mobile (Collapsible)

```typescript
// layout/Sidebar.tsx
import { useState } from "react";

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle */}
      <button
        className="d-lg-none btn btn-sm m-2"
        onClick={() => setOpen(!open)}
      >
        ☰ Menu
      </button>

      {/* Sidebar */}
      <nav
        className={`${
          open ? "show" : ""
        } d-lg-block bg-light p-3 position-fixed position-lg-static`}
        style={{ width: "250px", height: "100vh", zIndex: 999 }}
      >
        <ul className="nav flex-column">
          <li><a href="/dashboard">Dashboard</a></li>
          <li><a href="/catalog">Products</a></li>
          <li><a href="/inventory">Inventory</a></li>
        </ul>
      </nav>

      {/* Overlay mobile */}
      {open && (
        <div
          className="d-lg-none fixed-top"
          style={{ zIndex: 998, backgroundColor: "rgba(0,0,0,0.5)" }}
          onClick={() => setOpen(false)}
        ></div>
      )}
    </>
  );
}
```

### 14.2 Grid Responsive (Mobile → Desktop)

```typescript
// modules/catalog/pages/CatalogPage.tsx
export function CatalogPage() {
  return (
    <div className="container-fluid p-3">
      <div className="row g-3">
        {/* Sidebar: Full trên mobile, 3 col trên desktop */}
        <div className="col-12 col-lg-3">
          <FilterPanel />
        </div>

        {/* Content: Full trên mobile, 9 col trên desktop */}
        <div className="col-12 col-lg-9">
          <ProductTable />
        </div>
      </div>
    </div>
  );
}
```

---

## 15. Form – Giảm Input, Hiển Thị Rõ

### 15.1 Field Layout

```typescript
// Stacked mobile, inline desktop
<div className="row g-3">
  <div className="col-12 col-md-6">
    <label className="form-label">Product Name</label>
    <input className="form-control" />
  </div>
  <div className="col-12 col-md-6">
    <label className="form-label">Price</label>
    <input type="number" className="form-control" />
  </div>
  <div className="col-12 col-md-6">
    <label className="form-label">Stock</label>
    <input type="number" className="form-control" />
  </div>
  <div className="col-12 col-md-6">
    <label className="form-label">Status</label>
    <div>
      <div className="form-check form-check-inline">
        <input type="radio" name="status" value="active" />
        <label>Active</label>
      </div>
      <div className="form-check form-check-inline">
        <input type="radio" name="status" value="inactive" />
        <label>Inactive</label>
      </div>
    </div>
  </div>
</div>
```

---

## 16. Hiệu Năng & UX Metrics

### 16.1 Mục tiêu

- **First Contentful Paint (FCP)**: < 1.5s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Cumulative Layout Shift (CLS)**: < 0.1
- **Average action**: < 2 clicks

### 16.2 Optimization

```typescript
// Lazy load hình ảnh
<img loading="lazy" src="..." />

// Memoize components
export const ProductTable = memo(({ products }) => {
  return <table>...</table>;
}, (prev, next) => prev.products === next.products);

// Debounce search
const handleSearch = useMemo(
  () => debounce((term) => setSearch(term), 300),
  []
);
```

---

## 17. Checklist UI/UX Optimization

- [ ] Responsive: Desktop + Tablet + Mobile (tested)
- [ ] Inline CRUD (không modal)
- [ ] Expandable rows (chi tiết không popup)
- [ ] Delete với undo (không confirm modal)
- [ ] Radio/Toggle thay dropdown (khi ≤3 mục)
- [ ] Form stacked mobile, inline desktop
- [ ] Button >= 44px (touch-friendly)
- [ ] Bảng scroll ngang mobile (không resize)
- [ ] < 2 click/action trung bình
- [ ] Toàn bộ dữ liệu hiển thị (không ẩn)
- [ ] Breadcrumb hoặc Back button (navigate)
- [ ] Loading state (skeleton, spinner)

---

## 18. Triển khai UI Optimization – Frontend Dashboard (4 Jan 2026)

### 18.1 Các files cập nhật

#### Layout Components
- [layout/MainLayout.tsx](layout/MainLayout.tsx) - Responsive layout với fixed sidebar
- [layout/Sidebar.tsx](layout/Sidebar.tsx) - Collapsible mobile menu + fixed desktop
- [layout/Header.tsx](layout/Header.tsx) - Breadcrumb responsive + user info

#### Shared UI Components (Reusable)
- [shared/components/DeleteAction.tsx](shared/components/DeleteAction.tsx) - Delete với undo timer (5s)
- [shared/components/ExpandableRow.tsx](shared/components/ExpandableRow.tsx) - Chi tiết mở rộng không modal
- [shared/components/InlineEditor.tsx](shared/components/InlineEditor.tsx) - Chỉnh sửa inline trong bảng

#### Page & Module Components
- [pages/DashboardHomePage.tsx](pages/DashboardHomePage.tsx) - Dashboard overview responsive
- [modules/catalog/pages/CatalogPage.tsx](modules/catalog/pages/CatalogPage.tsx) - Catalog view tối giản
- [modules/catalog/components/ProductTable.tsx](modules/catalog/components/ProductTable.tsx) - Inline CRUD + expandable row
- [modules/products/pages/ProductsPage.tsx](modules/products/pages/ProductsPage.tsx) - Project selector (tabs không dropdown)
- [modules/products/components/ProductTable.tsx](modules/products/components/ProductTable.tsx) - Inline edit + delete + undo

### 18.2 Tính năng chuẩn

| Tính năng | Trước | Sau | Cải thiện |
|-----------|-------|-----|-----------|
| **Desktop & Mobile** | Fixed layout | Responsive grid, collapsible sidebar | ✅ Hoạt động tốt trên mobile |
| **Popup** | Modal xác nhận (5 thao tác) | 1-click delete + undo hoặc inline edit | ✅ Giảm 80% interaction |
| **CRUD Create** | Form modal | Inline form modal | ✅ 2 thao tác |
| **CRUD Read** | Bảng hiển thị | Expandable row + chi tiết | ✅ Không popup |
| **CRUD Update** | Modal form | Inline edit (✏️ → Save/Cancel) | ✅ 2 thao tác |
| **CRUD Delete** | Confirm modal | Delete + Undo (5s countdown) | ✅ 1 thao tác |
| **Dropdown** | Select HTML | Button tabs hoặc radio visible | ✅ Hiện thị đầy đủ |
| **Data** | Ẩn trong dropdown/collapse | Tất cả hiển thị bên ngoài | ✅ Transparency |
| **Loading** | Alert text | Spinner + skeleton | ✅ UX better |
| **Actions** | Btn-group narrow | Separate buttons responsive | ✅ Tap-friendly mobile |

### 18.3 Cấu trúc Layout Responsive

```
Desktop (>992px):
┌─────────────────────────────────┐
│  Sidebar (250px fixed)  Header  │
│  ┌──────────────────────────┐   │
│  │                          │   │
│  │   Main Content Area      │   │
│  │   (responsive grid)      │   │
│  │                          │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘

Mobile (<992px):
┌──────────────────┐
│  Header + Menu ☰ │
├──────────────────┤
│                  │
│ Main Content     │
│ (stacked 1 col)  │
│                  │
├──────────────────┤
│ Mobile Menu ☰    │
│ (overlay)        │
└──────────────────┘
```

### 18.4 Shared Components Usage

**DeleteAction** - 1-click delete + undo:
```tsx
<DeleteAction 
  id={product.id}
  onDelete={handleDelete}
  loading={loading}
/>
```

**ExpandableRow** - Chi tiết mở rộng:
```tsx
<ExpandableRow
  id={product.id}
  summary={<strong>{product.name}</strong>}
  details={<div>Full details here...</div>}
  actions={<button>Edit</button>}
/>
```

**InlineEditor** - Chỉnh sửa inline:
```tsx
<InlineEditor
  id={product.id}
  initialValue={product.name}
  onSave={handleSave}
  type="text"
/>
```

### 18.5 Bootstrap Grid System Used

```tsx
// Responsive columns: Mobile → Tablet → Desktop
<div className="row g-3">
  <div className="col-12 col-md-6 col-lg-3">
    Responsive widget
  </div>
</div>

// Responsive typography
<h1 className="h3">Mobile: h3, Desktop: h1</h1>

// Responsive display
<div className="d-none d-md-block">Show on tablet+</div>
<div className="d-md-none">Show on mobile</div>

// Responsive padding
<div className="p-3 p-md-4">Mobile: p-3, Desktop: p-4</div>
```

### 18.6 Performance Metrics (Target)

- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Cumulative Layout Shift: < 0.1
- Average action: < 2 clicks
- Mobile pagespeed: > 80

### 18.7 API Integration

**API không thay đổi**, chỉ cải thiện giao diện:
- Catalog API: `/api/catalog/products` (GET, POST, PUT, DELETE)
- Products API: `/api/products` (GET, POST, PUT, DELETE)
- Tenant API: `/api/tenants` (GET)

**Frontend gọi API không thay đổi**, chỉ thêm error handling, loading state tốt hơn.

### 18.8 Checklist Hoàn Thành

- [x] Responsive layout (desktop + mobile + tablet)
- [x] Collapsible sidebar mobile
- [x] Sticky header breadcrumb
- [x] Inline CRUD (không modal)
- [x] Delete + undo (không confirm modal)
- [x] Expandable rows (chi tiết không popup)
- [x] Radio button thay dropdown
- [x] Shared reusable components
- [x] Bootstrap CSS only (no framework)
- [x] Light theme white/gray
- [x] Tap-friendly buttons (44px+)
- [x] Responsive typography
- [x] Loading spinners
- [x] Error alerts
- [x] < 2 clicks per action

---

**Cập nhật: 4 Jan 2026**
- ✅ Mobile-first responsive layout
- ✅ Inline CRUD + Undo
- ✅ Expandable rows (no modal)
- ✅ Visible data (no dropdown)
- ✅ Minimal actions (< 2 clicks)
- ✅ Shared UI components (DeleteAction, ExpandableRow, InlineEditor)
- ✅ All modules updated (Catalog, Products, Dashboard)
- ✅ Bootstrap CSS only, no UI framework
- ✅ API không thay đổi, chỉ UI improvement