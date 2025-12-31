# PriceSync Frontend Dashboard

Triển khai dashboard frontend cho hệ thống SaaS theo kiến trúc tối giản.

## Nhanh chóng bắt đầu

### 1. Cài đặt dependencies
```bash
cd fontend/dashboard
npm install
```

### 2. Chạy development server
```bash
npm start
```

Mở [http://localhost:3000](http://localhost:3000) để xem trong browser.

### 3. Build cho production
```bash
npm run build
```

## Cấu trúc

- **shared/** - Utilities chung (api.ts, auth.ts)
- **layout/** - Layout cố định (MainLayout, Sidebar, Header)
- **pages/** - Trang chính (DashboardHomePage)
- **modules/** - Các module chức năng (catalog, inventory, etc.)
- **styles/** - CSS global (light theme)

## Nguyên tắc

✅ **Làm**
- React Function Components
- Bootstrap 5 CSS only (không JS)
- Fetch API ở Page level
- Manual route registry
- TypeScript khi có thể

❌ **Không làm**
- jQuery, UI framework nặng (AntD, MUI)
- CSS-in-JS, animation phức tạp
- Logic phức tạp ở component
- Bootstrap JS components
- Global state cho business data

## Module Registry

Thêm route mới vào [router.tsx](router.tsx):

```typescript
export const routeRegistry: RouteConfig[] = [
  {
    path: "/new-module",
    element: <NewModulePage />,
    module: "new_module",
    label: "New Module",
  },
];
```

## Styling

Dùng Bootstrap utility classes + global.css:

```tsx
<div className="p-4 mb-3 border rounded">
  <h5>Title</h5>
  <p className="text-muted">Description</p>
</div>
```

## API Integration

Mỗi module tự quản lý API:

```typescript
// modules/catalog/catalog.api.ts
export async function fetchProducts() {
  return api.get("/api/catalog/products");
}

// modules/catalog/pages/CatalogPage.tsx
useEffect(() => {
  fetchProducts().then(setProducts);
}, []);
```

## Kiểm tra

```bash
npm test
```

## Tài liệu

Xem chi tiết tại [SETUP.md](SETUP.md) và [../../font-end.md](../../font-end.md)

---

**Version**: 0.1.0  
**Last updated**: 31 Dec 2025
