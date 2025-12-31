# Dashboard Frontend Setup

## Cấu trúc thư mục

```
fontend/dashboard/
├── app.tsx                    # Main App component
├── router.tsx                 # Route registry (manual)
├── index.tsx                  # Entry point
├── index.html                 # HTML template
├── package.json               # Dependencies
├── shared/
│   ├── api.ts                 # API client wrapper
│   └── auth.ts                # Auth utilities
├── layout/
│   ├── MainLayout.tsx         # Main layout (Sidebar + Header + Content)
│   ├── Sidebar.tsx            # Navigation sidebar
│   └── Header.tsx             # Top header
├── pages/
│   └── DashboardHomePage.tsx   # Home dashboard
├── modules/
│   └── catalog/
│       ├── catalog.api.ts     # Catalog API client
│       ├── pages/
│       │   └── CatalogPage.tsx # Catalog page
│       └── components/
│           └── ProductTable.tsx # Product list table
└── styles/
    └── global.css             # Global styles (light theme)
```

## Nguyên tắc triển khai

### 1. **Phong cách code**
- React Function Components (không Class)
- TypeScript khi có thể
- Không dùng UI framework nặng (chỉ Bootstrap CSS)

### 2. **API Management**
- Mỗi module tự quản lý API client (`module.api.ts`)
- URL cố định, không sinh động
- Tập trung fetch dữ liệu ở Page level

### 3. **Routing**
- Manual route registry (không dynamic import)
- Mỗi route trong `routeRegistry` tương ứng 1 module backend
- Dễ debug, dễ tree-shake khi build

### 4. **Layout**
- Sidebar + Header cố định (không re-render khi đổi page)
- MainLayout wrap toàn bộ content
- Page component chịu trách nhiệm gọi API

### 5. **Component Structure**
```typescript
// ❌ Sai
<Layout apiCall={...} />

// ✅ Đúng
<Layout>
  <Page>
    <Component />
  </Page>
</Layout>
```

## Thêm module mới

### Bước 1: Tạo Backend Module
```
services/module_name/
├── domain/
├── infrastructure/
├── repositories/
└── services/
```

### Bước 2: Tạo Frontend Module
```bash
mkdir -p fontend/dashboard/modules/module_name/{pages,components}
```

### Bước 3: Thêm API Client
```typescript
// fontend/dashboard/modules/module_name/module_name.api.ts
import { api } from "../../shared/api";

export async function fetchData() {
  return api.get("/api/module_name/data");
}
```

### Bước 4: Tạo Page Component
```typescript
// fontend/dashboard/modules/module_name/pages/ModulePage.tsx
import { fetchData } from "../module_name.api";

export function ModulePage() {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    fetchData().then(res => setData(res));
  }, []);
  
  return <div>{/* Render data */}</div>;
}
```

### Bước 5: Thêm Route
```typescript
// fontend/dashboard/router.tsx
import { ModulePage } from "./modules/module_name/pages/ModulePage";

export const routeRegistry: RouteConfig[] = [
  // ... existing routes
  {
    path: "/module_name",
    element: <ModulePage />,
    module: "module_name",
    label: "Module Name",
  },
];
```

### Bước 6: Cập nhật Menu
```typescript
// fontend/dashboard/layout/Sidebar.tsx
const menuItems = [
  // ... existing items
  {
    label: "Module Name",
    path: "/module_name",
    icon: "📋",
  },
];
```

## Style Guide

### Color Palette
- **Primary**: #0066cc (Blue)
- **Background**: #f8f9fa (Light Gray)
- **Border**: #e5e5e5 (Gray)
- **Text**: #333 (Dark)
- **Text Muted**: #999 (Gray)

### Typography
- Font: System font stack (Segoe UI, Roboto, etc.)
- Base size: 14px
- Headings: 600 weight

### Spacing
- Base unit: 4px (Bootstrap rem default)
- Padding: p-3 (1rem), p-4 (1.5rem)
- Margin: m-3, m-4, mb-4 (margin-bottom)

### Components
- Border radius: 4px, 6px
- Box shadow: 0 1px 3px rgba(0,0,0,0.05)
- No animation, no gradient, no color scheme change

## Environment Variables

```
REACT_APP_API_URL=http://localhost:8000
```

## Build & Deploy

```bash
# Install dependencies
npm install

# Development
npm start

# Production build
npm run build

# Output: build/ folder
```

## Checklist

- [ ] Toàn bộ code React function component
- [ ] Không có logic phức tạp ở component (tách ra services/helpers)
- [ ] API call ở Page level, không ở Layout
- [ ] Styling dùng Bootstrap utility + global.css
- [ ] Không dùng animation, gradient
- [ ] Responsive design (mobile-first)
- [ ] Error handling có dialog/alert
- [ ] Loading state có placeholder/spinner
- [ ] Manual route registry (rõ ràng)
- [ ] TypeScript strict mode

---

**Last updated**: 31 Dec 2025
