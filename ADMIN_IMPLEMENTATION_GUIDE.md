# Admin Panel Implementation Guide

A comprehensive step-by-step procedure to add admin functionality to your FRESH application.

---

## 📋 Overview

This guide covers implementing:
1. **Backend Admin Routes** - CRUD operations for users, view all orchards, view all detection results
2. **Role-Based Access Control** - Restrict admin endpoints to admin users only
3. **Frontend Admin Dashboard** - UI for admin to manage users and view data
4. **Frontend-Backend Integration** - Connect frontend to new admin endpoints

---

## 🎯 Phase 1: Backend Implementation

### Step 1.1: Add Admin Role Check to Dependencies

**File:** `src/api/deps.py`

Add a new dependency function to verify admin access:

```python
async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to verify current user is an admin.
    Raises 403 Forbidden if user is not an admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this endpoint"
        )
    return current_user
```

### Step 1.2: Create Admin API Routes File

**File:** `src/api/admin.py` (NEW)

Create a new router with the following endpoints:

#### Endpoint 1: Get All Users
```python
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all users (paginated). 
    Optional filtering by role.
    """
```

#### Endpoint 2: Create User (Manual)
```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_admin(
    user: UserSignup,
    current_user: dict = Depends(get_current_admin)
):
    """
    Admin can create users manually without password signup.
    """
```

#### Endpoint 3: Update User
```python
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Update a user's information (name, role, email).
    """
```

#### Endpoint 4: Delete User
```python
@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """
    Delete a user from the system.
    """
```

#### Endpoint 5: Get All Orchards
```python
@router.get("/orchards", response_model=List[OrchardResponse])
async def get_all_orchards(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all orchards across all users.
    Optional filtering by specific user.
    """
```

#### Endpoint 6: Get All Detection Results
```python
@router.get("/detection-results", response_model=List[DetectionResponse])
async def get_all_detection_results(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    orchard_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all detection results from all users.
    Optional filtering by user or orchard.
    """
```

### Step 1.3: Create UserUpdate Schema

**File:** `src/schemas/user.py` (UPDATE)

Add a new schema for updating users:

```python
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    
    class Config:
        from_attributes = True
```

### Step 1.4: Register Admin Router

**File:** `main.py` (UPDATE)

Import and register the admin router:

```python
from src.api import admin_router

app.include_router(admin_router, prefix="/api/admin")
```

Also update `src/api/__init__.py` to export the admin_router.

### Step 1.5: Update User Service (Optional but Recommended)

**File:** `src/services/auth_service.py` (UPDATE)

Add helper functions for admin operations:

```python
def get_all_users(limit: int, offset: int, role: Optional[str] = None):
    """Retrieve all users with optional role filtering"""

def create_admin_user(user_data: UserSignup):
    """Create user from admin panel (handle password differently)"""

def update_user_by_id(user_id: str, user_update: UserUpdate):
    """Update user fields"""

def delete_user_by_id(user_id: str):
    """Delete user and cascade related data"""
```

### Step 1.6: Database Considerations

Run any migrations needed:
```sql
-- Ensure users table has proper indexes for admin queries
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- Ensure detection_results has proper indexes
CREATE INDEX idx_detection_results_user_id ON detection_results(user_id);
CREATE INDEX idx_detection_results_created_at ON detection_results(created_at DESC);
```

---

## 🎨 Phase 2: Frontend Implementation

### Step 2.1: Create Admin Layout

**File:** `src/app/admin/layout.tsx` (NEW)

Create a layout wrapper for admin pages:

```typescript
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Check user role here and redirect if not admin
  // Provide sidebar navigation
  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

### Step 2.2: Create Admin Pages

Create the following pages under `src/app/admin/`:

#### Users Management Page
**File:** `src/app/admin/users/page.tsx`

Features:
- List all users with pagination
- Filter by role
- Delete user button
- Edit user modal
- Create new user form

#### Orchards Page
**File:** `src/app/admin/orchards/page.tsx`

Features:
- List all orchards
- Filter by user
- View orchard details
- Pagination

#### Detection Results Page
**File:** `src/app/admin/detection-results/page.tsx`

Features:
- List all detection results
- Filter by user or orchard
- View result details
- Export data option
- Pagination

### Step 2.3: Create Admin Components

**File:** `src/components/admin/AdminSidebar.tsx` (NEW)

Navigation sidebar:

```typescript
const adminMenuItems = [
  { label: "Users", href: "/admin/users", icon: "Users" },
  { label: "Orchards", href: "/admin/orchards", icon: "Tree" },
  { label: "Detection Results", href: "/admin/detection-results", icon: "Image" },
  { label: "Dashboard", href: "/admin/dashboard", icon: "BarChart" },
];
```

**File:** `src/components/admin/UsersTable.tsx` (NEW)

Data table component for users with columns:
- Email
- Name
- Role
- Created Date
- Actions (Edit, Delete)

**File:** `src/components/admin/OrchardsTable.tsx` (NEW)

Data table component for orchards with columns:
- Name
- Owner
- Location
- Fruit Types
- Area
- Actions

**File:** `src/components/admin/DetectionResultsTable.tsx` (NEW)

Data table component for results with columns:
- Detection ID
- User
- Orchard
- Fruit Count
- Confidence
- Date
- Actions

### Step 2.4: Create API Service

**File:** `src/lib/api/admin.ts` (NEW)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const adminAPI = {
  // Users
  getAllUsers: async (limit = 100, offset = 0, role?: string) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (role) params.append("role", role);
    return fetch(`${API_BASE}/admin/users?${params}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });
  },

  createUser: async (userData) => {
    return fetch(`${API_BASE}/admin/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`
      },
      body: JSON.stringify(userData)
    });
  },

  updateUser: async (userId, userData) => {
    return fetch(`${API_BASE}/admin/users/${userId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`
      },
      body: JSON.stringify(userData)
    });
  },

  deleteUser: async (userId) => {
    return fetch(`${API_BASE}/admin/users/${userId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });
  },

  // Orchards
  getAllOrchards: async (limit = 100, offset = 0, userId?: string) => {
    // Similar pattern...
  },

  // Detection Results
  getAllDetectionResults: async (limit = 100, offset = 0, userId?: string, orchardId?: string) => {
    // Similar pattern...
  }
};
```

### Step 2.5: Update Authentication Store

**File:** `src/store/auth.ts` (UPDATE)

Ensure the auth store includes the user's role:

```typescript
interface User {
  id: string;
  email: string;
  full_name: string;
  role: "farmer" | "exporter" | "government" | "admin";
}

// Add helper to check if user is admin
export const isAdmin = (user: User) => user.role === "admin";
```

### Step 2.6: Add Admin Route Protection

**File:** `src/app/admin/page.tsx` (NEW)

Create a "Admin Dashboard" landing page with middleware to check admin access:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";

export default function AdminDashboard() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "admin")) {
      router.push("/unauthorized");
    }
  }, [user, isLoading, router]);

  return (
    <div>
      {/* Admin Dashboard Content */}
    </div>
  );
}
```

### Step 2.7: Update Navigation

**File:** `src/components/Navbar.tsx` (UPDATE)

Add admin link visible only to admin users:

```typescript
{user?.role === "admin" && (
  <Link href="/admin">Admin Panel</Link>
)}
```

---

## 🔗 Phase 3: Integration Steps

### Step 3.1: Test Backend Endpoints

```bash
# Get token first
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password123"}'

# Test admin endpoints
curl -X GET http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 3.2: Test Frontend-Backend Connection

1. Login with an admin account
2. Navigate to /admin
3. Test CRUD operations on users
4. Test filtering on orchards
5. Test viewing detection results

### Step 3.3: Environment Variables

Ensure these are set in both backend and frontend:

**Backend (.env):**
```
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
JWT_SECRET=your_secret
DEBUG=False (for production)
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
# or for production
NEXT_PUBLIC_API_URL=https://your-api.com/api
```

---

## 📝 Phase 4: Additional Considerations

### Error Handling
- Add proper error messages for admin operations
- Implement toast notifications for success/failure
- Handle cascading deletes carefully (deleting user → orphaned data)

### Security
- Add CSRF protection for admin routes
- Implement request logging for audit trail
- Add rate limiting to prevent abuse
- Validate all inputs server-side

### Performance
- Add pagination to all list endpoints (already included)
- Consider caching frequently accessed data
- Add database indexes on filtered columns
- Implement lazy loading for large datasets

### Testing
- Write unit tests for admin service functions
- Write integration tests for admin endpoints
- Test role-based access control thoroughly
- Test frontend page access restrictions

---

## 📚 File Summary

### Backend Files to Create:
```
src/api/admin.py                  - Main admin routes
```

### Backend Files to Update:
```
src/api/deps.py                   - Add admin check
src/schemas/user.py               - Add UserUpdate schema
src/api/__init__.py               - Export admin_router
main.py                           - Register admin router
src/services/auth_service.py      - Add admin helper functions (optional)
```

### Frontend Files to Create:
```
src/app/admin/layout.tsx
src/app/admin/page.tsx
src/app/admin/users/page.tsx
src/app/admin/orchards/page.tsx
src/app/admin/detection-results/page.tsx
src/components/admin/AdminSidebar.tsx
src/components/admin/UsersTable.tsx
src/components/admin/OrchardsTable.tsx
src/components/admin/DetectionResultsTable.tsx
src/lib/api/admin.ts
```

### Frontend Files to Update:
```
src/store/auth.ts                 - Add role type
src/components/Navbar.tsx         - Add admin link
src/app/layout.tsx                - Update as needed
```

---

## 🚀 Quick Start Order

1. **First:** Add `get_current_admin` to `src/api/deps.py`
2. **Second:** Create `src/api/admin.py` with all endpoints
3. **Third:** Update `main.py` to include admin router
4. **Fourth:** Test backend endpoints with curl
5. **Fifth:** Create frontend admin pages and components
6. **Sixth:** Connect frontend to backend API
7. **Seventh:** Test full integration
8. **Eighth:** Add proper error handling and validation

---

## 🔄 Database Migration (if needed)

If you need to set up admin user initially:

```sql
-- Insert admin user (adjust password hash as needed)
INSERT INTO users (id, email, password_hash, full_name, role, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'admin@fresh.app',
  'hashed_password_here',
  'Administrator',
  'admin',
  NOW(),
  NOW()
);
```

---

## 📞 Troubleshooting

### Issue: Admin routes return 403
- **Solution:** Verify user token includes correct role claim
- Check `get_current_admin` dependency

### Issue: Frontend can't fetch admin data
- **Solution:** Check CORS settings in `main.py`
- Verify token is being sent in Authorization header
- Check API_BASE URL matches backend

### Issue: Users can access /admin without permission
- **Solution:** Add client-side route protection
- Use middleware or useEffect to check role
- Consider using next-auth for better security

---

## 📖 References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Next.js App Router: https://nextjs.org/docs/app
- Supabase Client: https://supabase.com/docs/reference/python/

