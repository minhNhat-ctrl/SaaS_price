# Dashboard Frontend - Quick Reference

## 📂 Cấu trúc nhanh

```
fontend/dashboard/
├── app.tsx              # Main component
├── router.tsx           # Routes (manual registry)
├── index.tsx            # Entry point
├── shared/              # API, auth, config
├── layout/              # Sidebar, Header, MainLayout
├── pages/               # Home page
├── modules/             # Feature modules (catalog, etc.)
└── styles/              # CSS (light theme)
```

---

## 🛠️ Sử dụng nhanh

### Khởi động

```bash
cd fontend/dashboard
npm install
npm start
```

### Thêm Route Mới

**File: `router.tsx`**
```typescript
import { NewPage } from "./modules/new/pages/NewPage";

export const routeRegistry: RouteConfig[] = [
  {
    path: "/new",
    element: <NewPage />,
    module: "new",
    label: "New",
  },
];
```

### Tạo API Client

**File: `modules/inventory/inventory.api.ts`**
```typescript
import { api } from "../../shared/api";

export async function fetchInventory() {
  return api.get("/api/inventory/items");
}

export async function updateInventory(id: string, data: unknown) {
  return api.put(`/api/inventory/items/${id}`, data);
}
```

### Tạo Page

**File: `modules/inventory/pages/InventoryPage.tsx`**
```typescript
import { useState, useEffect } from "react";
import { fetchInventory } from "../inventory.api";

export function InventoryPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInventory()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Inventory</h1>
      {loading ? <p>Loading...</p> : <p>Data: {data.length}</p>}
    </div>
  );
}
```

### Tạo Component

**File: `modules/inventory/components/InventoryTable.tsx`**
```typescript
import { memo } from "react";

interface InventoryTableProps {
  items: any[];
}

export const InventoryTable = memo(({ items }: InventoryTableProps) => (
  <table className="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Quantity</th>
      </tr>
    </thead>
    <tbody>
      {items.map(item => (
        <tr key={item.id}>
          <td>{item.name}</td>
          <td>{item.quantity}</td>
        </tr>
      ))}
    </tbody>
  </table>
));
```

---

## 🎨 Styling Quick Tips

```tsx
// Bootstrap utilities
<div className="p-4 mb-3 border rounded">
  <h5>Title</h5>
  <p className="text-muted">Subtitle</p>
</div>

// Inline styles (khi cần custom)
<div style={{ display: "flex", gap: "10px" }}>
  Content
</div>

// Card
<div className="card">
  <div className="card-body">
    Content
  </div>
</div>

// Colors
- Primary: #0066cc (links, active)
- Background: #f8f9fa (page bg)
- Border: #e5e5e5 (dividers)
- Text: #333 (dark)
- Muted: #999 (secondary text)
```

---

## 📡 API Integration

### Fetch từ Backend

```typescript
// Simple GET
export async function getUsers() {
  return api.get<{ data: User[] }>("/api/users");
}

// POST with data
export async function createUser(input: CreateUserInput) {
  return api.post<{ data: User }>("/api/users", input);
}

// PUT with ID
export async function updateUser(id: string, input: Partial<User>) {
  return api.put<{ data: User }>(`/api/users/${id}`, input);
}

// DELETE
export async function deleteUser(id: string) {
  return api.delete(`/api/users/${id}`);
}
```

### Error Handling

```typescript
try {
  const data = await fetchUsers();
  setUsers(data);
} catch (error) {
  setError("Failed to load users");
  console.error(error);
}
```

---

## 🔐 Authentication

```typescript
import { getAuthToken, setAuthToken, logout } from "@/shared/auth";

// Set token (after login)
setAuthToken("eyJhbG...");

// Get token
const token = getAuthToken();

// Check authenticated
if (isAuthenticated()) {
  // Show dashboard
}

// Logout
logout(); // Clears token, redirects to /login
```

---

## 📋 Checklist khi thêm Module

- [ ] Tạo folder `modules/new_module/`
- [ ] Tạo `new_module.api.ts` (API client)
- [ ] Tạo `pages/NewModulePage.tsx` (page component)
- [ ] Tạo `components/` (reusable components)
- [ ] Import page vào `router.tsx`
- [ ] Thêm route vào `routeRegistry`
- [ ] Thêm menu item vào `Sidebar.tsx`
- [ ] Test fetch data
- [ ] Test error handling
- [ ] Test loading state
- [ ] Check responsive (mobile)
- [ ] Review styling (light theme)

---

## ⚡ Performance Tips

- ✅ Fetch data ở page level, không layout
- ✅ Sidebar không re-render khi đổi page
- ✅ Dùng `memo()` cho component với props phức tạp
- ✅ Không dùng inline function khi pass props
- ✅ Lazy load data (pagination, infinite scroll)
- ❌ Không dùng global state cho business data
- ❌ Không re-fetch data liên tục

---

## 🚀 Deploy

```bash
# Build
npm run build

# Output: build/ folder

# Deploy to server
scp -r build/ user@server:/var/www/dashboard

# Set env var
REACT_APP_API_URL=https://api.example.com
```

---

## 📚 File References

| File | Tác dụng |
|------|---------|
| `shared/api.ts` | Fetch wrapper, auth header |
| `shared/auth.ts` | Token, logout management |
| `shared/config.ts` | Constants, API endpoints |
| `layout/MainLayout.tsx` | Layout wrapper |
| `layout/Sidebar.tsx` | Navigation menu |
| `router.tsx` | Route registry |

---

**Version**: 0.1.0  
**Last**: 31 Dec 2025
