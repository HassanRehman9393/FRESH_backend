# Admin API Quick Reference

## Base URL
```
http://localhost:8000/api/admin
```

## Required Headers
```
Authorization: Bearer <ADMIN_JWT_TOKEN>
Content-Type: application/json
```

---

## Endpoints

### Users Management

#### 1. List All Users
```
GET /admin/users
```
**Parameters:**
- `limit`: 1-1000 (default: 100)
- `offset`: ≥ 0 (default: 0)
- `role`: Optional - farmer|exporter|government|admin

**Response:** `[UserResponse]`
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "farmer"
  }
]
```

---

#### 2. Create User
```
POST /admin/users
```
**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "role": "farmer"
}
```

**Response:** `UserResponse` (201 Created)

---

#### 3. Update User
```
PUT /admin/users/{user_id}
```
**Request:** (all fields optional)
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "role": "exporter"
}
```

**Response:** `UserResponse` (200 OK)

---

#### 4. Delete User
```
DELETE /admin/users/{user_id}
```

**Response:** Empty (204 No Content)

**Note:** Cannot delete your own account

---

### Orchards Management

#### 5. List All Orchards
```
GET /admin/orchards
```
**Parameters:**
- `limit`: 1-1000 (default: 100)
- `offset`: ≥ 0 (default: 0)
- `user_id`: Optional - filter by user

**Response:** `[OrchardResponse]`
```json
[
  {
    "id": "uuid",
    "name": "Mango Orchard",
    "user_id": "uuid",
    "latitude": 31.5204,
    "longitude": 74.3587,
    "area_hectares": 10.5,
    "fruit_types": ["mango"],
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### Detection Results Management

#### 6. List All Detection Results
```
GET /admin/detection-results
```
**Parameters:**
- `limit`: 1-1000 (default: 100)
- `offset`: ≥ 0 (default: 0)
- `user_id`: Optional - filter by user
- `orchard_id`: Optional - filter by orchard

**Response:** `[DetectionResponse]`
```json
[
  {
    "detection_id": "uuid",
    "user_id": "uuid",
    "image_id": "uuid",
    "orchard_id": "uuid",
    "fruit_type": "mango",
    "confidence": 0.95,
    "bounding_box": {
      "x": 100,
      "y": 150,
      "width": 200,
      "height": 250
    },
    "classification": {
      "ripeness_level": "ripe",
      "ripeness_confidence": 0.92,
      "color": "yellow",
      "size": "large",
      "quality_score": 85,
      "defects": []
    },
    "created_at": "2024-01-15T10:30:00Z",
    "annotated_image_url": "https://...",
    "annotated_image_filename": "annotated_uuid.jpg"
  }
]
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Deletion successful |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Non-admin user |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Email already in use |
| 500 | Server Error - Internal error |

---

## Example Workflows

### Create and Manage a User

```bash
# 1. Login to get admin token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}'
# Returns: { "access_token": "eyJ...", ... }

# 2. Create a new user
curl -X POST http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "email":"farmer@example.com",
    "password":"secure123",
    "full_name":"Jane Farmer",
    "role":"farmer"
  }'

# 3. Update the user
curl -X PUT http://localhost:8000/api/admin/users/{user_id} \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"role":"exporter"}'

# 4. View user's orchards
curl -X GET "http://localhost:8000/api/admin/orchards?user_id={user_id}" \
  -H "Authorization: Bearer eyJ..."

# 5. View user's detection results
curl -X GET "http://localhost:8000/api/admin/detection-results?user_id={user_id}" \
  -H "Authorization: Bearer eyJ..."

# 6. Delete the user
curl -X DELETE http://localhost:8000/api/admin/users/{user_id} \
  -H "Authorization: Bearer eyJ..."
```

---

## Error Response Format

All errors follow this format:
```json
{
  "detail": "Error description"
}
```

Example:
```json
{
  "detail": "Only admin users can access this endpoint"
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- UUID format for all IDs
- Email addresses are unique across the system
- Passwords must be at least 8 characters
- Bounding boxes are automatically converted from internal format
- Pagination uses inclusive range (offset to offset+limit-1)
- Role must be one of: farmer, exporter, government, admin

