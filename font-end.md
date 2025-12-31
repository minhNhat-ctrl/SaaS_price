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