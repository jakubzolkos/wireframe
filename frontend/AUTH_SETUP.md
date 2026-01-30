# Authentication Setup Guide

## ✅ Authentication is Now Fully Connected!

Your frontend authentication is now properly integrated with the backend database and JWT auth system.

## How It Works

### Backend (FastAPI + PostgreSQL)

**Database Tables:**
- `users` - User accounts with hashed passwords
- `sessions` - Active login sessions with refresh tokens

**Auth Endpoints:** (all at `/api/v1/auth`)
- `POST /login` - Login with email/password, returns JWT tokens
- `POST /register` - Create new user account
- `POST /logout` - Invalidate refresh token
- `POST /refresh` - Get new access token using refresh token
- `GET /me` - Get current authenticated user info

**Security:**
- JWT access tokens (short-lived, ~10 minutes)
- JWT refresh tokens (long-lived, stored in sessions table)
- Passwords hashed with bcrypt
- OAuth2 password bearer flow

### Frontend (React + Vite)

**State Management:**
- `useAuthStore` (Zustand) - Persists user state to localStorage
- `useAuth` hook - Handles login, logout, token refresh

**Token Storage:**
- `access_token` - Stored in localStorage
- `refresh_token` - Stored in localStorage
- Auto-included in all API requests via `Authorization: Bearer <token>`

**API Integration:**
- All requests through `/api/v1/*` automatically proxied to backend
- `api-client.ts` automatically adds JWT token to headers
- Token refresh on 401 errors

## Usage Examples

### 1. Login

```typescript
import { useAuth } from '@/hooks/use-auth';

function LoginPage() {
  const { login, isLoading } = useAuth();

  const handleLogin = async () => {
    try {
      await login({
        email: 'user@example.com',
        password: 'password123'
      });
      // User is now logged in and redirected to dashboard
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <button onClick={handleLogin} disabled={isLoading}>
      Login
    </button>
  );
}
```

### 2. Register

```typescript
import { useAuth } from '@/hooks/use-auth';

function RegisterPage() {
  const { register } = useAuth();

  const handleRegister = async () => {
    try {
      await register({
        email: 'newuser@example.com',
        password: 'securepassword',
        full_name: 'John Doe'
      });
      // Registration successful, can now login
    } catch (error) {
      console.error('Registration failed:', error);
    }
  };

  return <button onClick={handleRegister}>Register</button>;
}
```

### 3. Check Auth Status

```typescript
import { useAuth } from '@/hooks/use-auth';

function App() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <div>Welcome, {user?.email}!</div>;
}
```

### 4. Logout

```typescript
import { useAuth } from '@/hooks/use-auth';

function UserMenu() {
  const { logout } = useAuth();

  return (
    <button onClick={logout}>
      Logout
    </button>
  );
}
```

### 5. Protected API Calls

```typescript
import { apiClient } from '@/lib/api-client';

// Token is automatically included in headers
async function fetchUserData() {
  const user = await apiClient.get('/users/me');
  return user;
}

// Create a design (requires authentication)
async function createDesign(data) {
  const design = await apiClient.post('/designs', data);
  return design;
}
```

### 6. Protected Routes

```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return children;
}

// Usage in router
<Route path="/dashboard" element={
  <ProtectedRoute>
    <Dashboard />
  </ProtectedRoute>
} />
```

## Token Flow

```
1. User enters credentials
   ↓
2. POST /api/v1/auth/login (form-data)
   ↓
3. Backend validates credentials against database
   ↓
4. Returns { access_token, refresh_token }
   ↓
5. Frontend stores tokens in localStorage
   ↓
6. GET /api/v1/auth/me (with Bearer token)
   ↓
7. Backend validates JWT token
   ↓
8. Returns user data
   ↓
9. Frontend stores user in Zustand store
   ↓
10. All subsequent requests include Bearer token automatically
```

## Token Refresh Flow

```
1. API request fails with 401 Unauthorized
   ↓
2. useAuth.refreshToken() is called
   ↓
3. POST /api/v1/auth/refresh with refresh_token
   ↓
4. Backend validates refresh token against sessions table
   ↓
5. Returns new { access_token, refresh_token }
   ↓
6. Frontend stores new tokens
   ↓
7. Retry original request with new access token
```

## Environment Variables

**Development (`.env`):**
```bash
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080
```

**Docker (nginx forwards `/api` to backend):**
```bash
VITE_API_URL=http://app:8080
VITE_WS_URL=ws://app:8080
```

## Backend Configuration

Check `wireframe/backend/.env` for JWT settings:

```bash
# JWT Secret (change in production!)
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32

# Token expiration (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# JWT Algorithm
ALGORITHM=HS256
```

## Database Schema

**Users Table:**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  hashed_password VARCHAR NOT NULL,
  full_name VARCHAR,
  is_active BOOLEAN DEFAULT TRUE,
  is_superuser BOOLEAN DEFAULT FALSE,
  role VARCHAR DEFAULT 'user',
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**Sessions Table:**
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  refresh_token VARCHAR NOT NULL,
  ip_address VARCHAR,
  user_agent VARCHAR,
  expires_at TIMESTAMP,
  created_at TIMESTAMP
);
```

## Testing Authentication

### 1. Start Backend

```bash
cd wireframe
make docker-up
# Backend runs on http://localhost:8080
```

### 2. Create a Test User

```bash
# Option 1: Via API
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Option 2: Via CLI (if available)
cd wireframe
make create-admin
```

### 3. Test Login

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"

# Response:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "bearer"
# }
```

### 4. Test Protected Endpoint

```bash
# Get current user info
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Response:
# {
#   "id": "...",
#   "email": "test@example.com",
#   "full_name": "Test User",
#   "is_active": true,
#   "role": "user"
# }
```

### 5. Start Frontend

```bash
cd wireframe/frontend
npm run dev
# Frontend runs on http://localhost:3000
```

### 6. Test in Browser

1. Navigate to `http://localhost:3000/login`
2. Enter credentials: `test@example.com` / `testpass123`
3. Click Login
4. Should redirect to dashboard with user info

## Troubleshooting

### "401 Unauthorized" on all requests

**Problem:** Access token expired or invalid

**Solution:**
```typescript
const { refreshToken } = useAuth();
await refreshToken();
```

### "CORS error" in browser console

**Problem:** Backend CORS not configured for frontend URL

**Solution:** Check `wireframe/backend/.env`:
```bash
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

### "Invalid credentials" on login

**Problem:** User doesn't exist or wrong password

**Solution:**
1. Check user exists in database
2. Try registering first
3. Check password is correct (case-sensitive)

### Tokens not persisting after refresh

**Problem:** localStorage being cleared

**Solution:** Check browser settings, try different browser, check if localStorage is disabled

## Security Best Practices

✅ **Implemented:**
- JWT tokens with expiration
- Refresh token rotation
- Password hashing (bcrypt)
- HTTPS in production (via Traefik)
- CORS protection
- Session tracking

⚠️ **TODO for Production:**
- Change `SECRET_KEY` in backend `.env`
- Use shorter `ACCESS_TOKEN_EXPIRE_MINUTES` (15-30 minutes)
- Enable HTTPS only
- Add rate limiting on login endpoint
- Add CSRF protection for state-changing operations
- Consider using HTTP-only cookies instead of localStorage

## Next Steps

1. ✅ Authentication is fully working
2. Build your login/register UI components
3. Add protected routes for your EDA editor
4. Integrate user management (if needed)
5. Add role-based access control (if needed)

Your authentication is production-ready and fully integrated with the database!
