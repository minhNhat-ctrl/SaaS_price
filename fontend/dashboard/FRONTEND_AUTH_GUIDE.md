# Frontend Authentication Setup Guide

## Overview

Frontend đã được cấu hình với authentication system hoàn chỉnh, bao gồm:
- Login / Signup pages
- Profile management
- Protected routes
- Session management

## Cấu trúc Frontend

```
fontend/dashboard/src/
├── app.tsx                      # Main app với AuthProvider
├── router.tsx                   # Route configuration
├── pages/
│   ├── LoginPage.tsx           # Login form
│   ├── SignupPage.tsx          # Signup form
│   ├── ProfilePage.tsx         # User profile management
│   ├── AuthPages.css           # Styling cho auth pages
│   └── DashboardHomePage.tsx   # Protected home page
├── shared/
│   ├── AuthContext.tsx         # Auth state management
│   ├── ProtectedRoute.tsx      # Route wrapper cho auth
│   ├── api.ts                  # API client
│   └── auth.ts                 # Auth utilities (deprecated - use AuthContext)
└── layout/
    ├── MainLayout.tsx          # Main layout wrapper
    ├── Header.tsx              # Header với user info & logout
    └── Sidebar.tsx             # Navigation sidebar
```

## API Integration

Frontend kết nối với backend API theo chuẩn SaaS:

### Authentication Endpoints

- `POST /api/identity/signup/` - Đăng ký tài khoản
- `POST /api/identity/login/` - Đăng nhập
- `POST /api/identity/logout/` - Đăng xuất
- `GET /api/identity/check-auth/` - Kiểm tra trạng thái đăng nhập

### Profile Management Endpoints

- `GET /api/accounts/profile/` - Lấy thông tin profile
- `POST /api/accounts/profile/update/` - Cập nhật profile
- `GET /api/accounts/preferences/` - Lấy preferences
- `POST /api/accounts/preferences/update/` - Cập nhật preferences

## Setup Instructions

### 1. Install Dependencies

```bash
cd fontend/dashboard
npm install
```

### 2. Environment Configuration

Tạo file `.env.development`:

```env
# Development - same domain as backend
REACT_APP_API_URL=http://localhost:8005

# Production
# REACT_APP_API_URL=http://dj.2kvietnam.com
```

### 3. Run Development Server

```bash
npm start
```

App sẽ chạy tại: `http://localhost:3000`

### 4. Build for Production

```bash
npm run build
```

## Authentication Flow

### 1. User Visits App

```
App loads → AuthProvider checks auth status → 
  ├─ Authenticated → Show protected routes
  └─ Not authenticated → Redirect to /login
```

### 2. Login Process

```
User enters credentials → 
  POST /api/identity/login/ → 
    ├─ Success: Store user in context → Navigate to dashboard
    └─ Error: Show error message
```

### 3. Protected Routes

```tsx
// All routes wrapped in ProtectedRoute
<ProtectedRoute>
  <MainLayout>
    <Routes>
      <Route path="/" element={<DashboardHomePage />} />
      <Route path="/profile" element={<ProfilePage />} />
      ...
    </Routes>
  </MainLayout>
</ProtectedRoute>
```

### 4. Logout Process

```
User clicks logout → 
  POST /api/identity/logout/ → 
    Clear user context → 
      Redirect to /login
```

## Using Auth in Components

### Get Current User

```tsx
import { useAuth } from '../shared/AuthContext';

function MyComponent() {
  const { user, isAuthenticated } = useAuth();
  
  return (
    <div>
      {isAuthenticated && <p>Welcome {user?.email}</p>}
    </div>
  );
}
```

### Programmatic Login

```tsx
import { useAuth } from '../shared/AuthContext';

function LoginForm() {
  const { login } = useAuth();
  
  const handleSubmit = async (e) => {
    try {
      await login(email, password);
      navigate('/');
    } catch (error) {
      console.error('Login failed:', error);
    }
  };
  
  return <form onSubmit={handleSubmit}>...</form>;
}
```

### Programmatic Logout

```tsx
import { useAuth } from '../shared/AuthContext';

function Header() {
  const { logout } = useAuth();
  
  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };
  
  return <button onClick={handleLogout}>Logout</button>;
}
```

## Session Management

- **Storage:** Django session cookies (automatic)
- **Credentials:** `credentials: 'include'` trong fetch requests
- **Persistence:** User info stored in localStorage for quick checks
- **Security:** CSRF protection cần được enable trong production

## Adding New Protected Pages

### 1. Create Page Component

```tsx
// src/pages/NewPage.tsx
export const NewPage: React.FC = () => {
  return <div>New Protected Page</div>;
};
```

### 2. Add to Router

```tsx
// src/router.tsx
import { NewPage } from "./pages/NewPage";

export const routeRegistry: RouteConfig[] = [
  // ... existing routes
  {
    path: "/new-page",
    element: <NewPage />,
    module: "new_module",
    label: "New Page",
    protected: true,
  },
];
```

### 3. Add to Sidebar (Optional)

```tsx
// src/layout/Sidebar.tsx
const menuItems: MenuItem[] = [
  // ... existing items
  {
    label: "New Page",
    path: "/new-page",
    icon: "🆕",
  },
];
```

## Styling

Auth pages sử dụng custom CSS với gradient background:

- **Primary color:** `#667eea`
- **Secondary color:** `#764ba2`
- **Gradient:** `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`

Các component khác sử dụng Bootstrap 5.

## Troubleshooting

### 1. CORS Errors

Nếu frontend chạy trên domain khác với backend:

```python
# config/settings.py
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]

CORS_ALLOW_CREDENTIALS = True
```

### 2. Session Not Persisting

Đảm bảo:
- `credentials: 'include'` trong tất cả fetch requests
- Cookie domain được cấu hình đúng
- HTTPS trong production

### 3. Redirect Loop

Kiểm tra:
- `/api/identity/check-auth/` endpoint hoạt động
- Cookie được gửi kèm request
- Backend trả về đúng format response

## Production Deployment

### 1. Build

```bash
npm run build
```

### 2. Serve với Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Serve React app
    location / {
        root /var/www/dashboard/build;
        try_files $uri /index.html;
    }
    
    # Proxy API requests to Django
    location /api/ {
        proxy_pass http://localhost:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Environment Variables

Production `.env.production`:

```env
REACT_APP_API_URL=https://your-domain.com
```

## Security Considerations

1. **CSRF Protection:** Enable trong production
2. **HTTPS:** Bắt buộc cho production
3. **Session Security:** Configure session timeout appropriately
4. **XSS Protection:** React tự động escape, nhưng cẩn thận với `dangerouslySetInnerHTML`
5. **Password Policy:** Enforce ở backend (min 8 chars đã có)

## Next Steps

- [ ] Implement email verification flow
- [ ] Add password reset functionality
- [ ] Implement 2FA (optional)
- [ ] Add social login (Google, GitHub)
- [ ] Profile avatar upload
- [ ] User preferences management (theme, language)
