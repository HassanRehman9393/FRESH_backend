# FRESH Backend Deployment

**Railway Deployment:**
https://freshbackend-production-096a.up.railway.app/

## API Endpoints

### POST /auth/signup
- Sample Input:
```json
{
	"email": "alice@example.com",
	"password": "SuperSecret123",
	"full_name": "Alice Smith",
	"role": "farmer"
}
```
- Sample Output:
```json
{
	"id": "b1a2c3d4-5678-90ab-cdef-1234567890ab",
	"email": "alice@example.com",
	"full_name": "Alice Smith",
	"role": "farmer",
	"auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/auth/signup \
		-H "Content-Type: application/json" \
		-d '{"email":"alice@example.com","password":"SuperSecret123","full_name":"Alice Smith","role":"farmer"}'
```

### POST /auth/login
- Sample Input:
```json
{
	"email": "alice@example.com",
	"password": "SuperSecret123"
}
```
- Sample Output:
```json
{
	"id": "b1a2c3d4-5678-90ab-cdef-1234567890ab",
	"email": "alice@example.com",
	"full_name": "Alice Smith",
	"role": "farmer",
	"auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"alice@example.com","password":"SuperSecret123"}'
```

### GET /auth/google/login
- Sample Output:
```json
{
	"auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```
- Curl:
```
curl https://freshbackend-production-096a.up.railway.app/auth/google/login
```

### GET /auth/google/callback
- Sample Input: Query params `code=4/0AX4XfWg...&state=xyz`
- Sample Output:
```json
{
	"id": "b1a2c3d4-5678-90ab-cdef-1234567890ab",
	"email": "alice@example.com",
	"full_name": "Alice Smith",
	"role": "farmer",
	"auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- Curl:
```
curl "https://freshbackend-production-096a.up.railway.app/auth/google/callback?code=4/0AX4XfWgEXAMPLE&state=xyz"
```

### POST /auth/google/callback
- Sample Input:
```json
{
	"code": "4/0AX4XfWgEXAMPLE",
	"state": "xyz"
}
```
- Sample Output:
```json
{
	"id": "b1a2c3d4-5678-90ab-cdef-1234567890ab",
	"email": "alice@example.com",
	"full_name": "Alice Smith",
	"role": "farmer",
	"auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/auth/google/callback \
		-H "Content-Type: application/json" \
		-d '{"code":"4/0AX4XfWgEXAMPLE","state":"xyz"}'
```

### GET /health
- Sample Output:
```json
{
	"status": "healthy",
	"service": "FRESH Backend API",
	"version": "1.0.0",
	"database": "connected"
}
```
- Curl:
```
curl https://freshbackend-production-096a.up.railway.app/health
```

### GET /docs
- Output: Swagger/OpenAPI UI
- Curl:
```
curl https://freshbackend-production-096a.up.railway.app/docs
```

## Image Management Endpoints

### POST /api/images/upload
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Form data with file upload
- Sample Output:
```json
{
	"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"file_path": "https://project.supabase.co/storage/v1/object/public/images/3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
	"file_name": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
	"metadata": {
		"original_filename": "sample_fruit.jpg",
		"storage_filename": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
		"content_type": "image/jpeg"
	},
	"created_at": "2025-10-05T12:30:45.123Z"
}
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/api/images/upload \
	-H "Authorization: Bearer YOUR_JWT_TOKEN" \
	-F "file=@sample_fruit.jpg"
```

### POST /api/images/batch-upload
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Form data with multiple file uploads
- Sample Output:
```json
[
	{
		"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"file_path": "https://project.supabase.co/storage/v1/object/public/images/3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
		"file_name": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
		"metadata": {
			"original_filename": "fruit1.jpg",
			"storage_filename": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
			"content_type": "image/jpeg"
		},
		"created_at": "2025-10-05T12:30:45.123Z"
	},
	{
		"id": "4fb95f64-5817-4662-b4fc-3d963f77bfb7",
		"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"file_path": "https://project.supabase.co/storage/v1/object/public/images/4fb95f64-5817-4662-b4fc-3d963f77bfb7.jpg",
		"file_name": "4fb95f64-5817-4662-b4fc-3d963f77bfb7.jpg",
		"metadata": {
			"original_filename": "fruit2.jpg",
			"storage_filename": "4fb95f64-5817-4662-b4fc-3d963f77bfb7.jpg",
			"content_type": "image/jpeg"
		},
		"created_at": "2025-10-05T12:31:15.456Z"
	}
]
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/api/images/batch-upload \
	-H "Authorization: Bearer YOUR_JWT_TOKEN" \
	-F "files=@fruit1.jpg" \
	-F "files=@fruit2.jpg"
```

### GET /api/images/{image_id}
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Path parameter `image_id=3fa85f64-5717-4562-b3fc-2c963f66afa6`
- Sample Output:
```json
{
	"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"file_path": "https://project.supabase.co/storage/v1/object/public/images/3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
	"file_name": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
	"metadata": {
		"original_filename": "sample_fruit.jpg",
		"storage_filename": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
		"content_type": "image/jpeg"
	},
	"created_at": "2025-10-05T12:30:45.123Z"
}
```
- Curl:
```
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
	https://freshbackend-production-096a.up.railway.app/api/images/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

### DELETE /api/images/{image_id}
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Path parameter `image_id=3fa85f64-5717-4562-b3fc-2c963f66afa6`
- Sample Output: 204 No Content (empty response body)
- Curl:
```
curl -X DELETE \
	-H "Authorization: Bearer YOUR_JWT_TOKEN" \
	https://freshbackend-production-096a.up.railway.app/api/images/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

## Object Detection Endpoints

### POST /api/detection/batch-fruit
- **Authentication Required**: Yes (Bearer token)
- Sample Input:
```json
{
	"image_ids": [
		"3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"4fb95f64-5817-4662-b4fc-3d963f77bfb7"
	]
}
```
- Sample Output:
```json
{
	"results": [
		{
			"detection_id": "5fc96f74-5927-4772-b5fc-4e074f88cgc8",
			"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
			"image_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
			"fruit_type": "orange",
			"confidence": 0.95,
			"bounding_box": {
				"x": 100.0,
				"y": 100.0,
				"width": 200.0,
				"height": 200.0
			},
			"created_at": "2025-10-05T12:35:30.789Z"
		},
		{
			"detection_id": "6gd07g85-6037-4883-c6gd-5f185g99dhd9",
			"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
			"image_id": "4fb95f64-5817-4662-b4fc-3d963f77bfb7",
			"fruit_type": "orange",
			"confidence": 0.95,
			"bounding_box": {
				"x": 100.0,
				"y": 100.0,
				"width": 200.0,
				"height": 200.0
			},
			"created_at": "2025-10-05T12:35:31.123Z"
		}
	],
	"total_count": 2,
	"success_count": 2,
	"failed_count": 0
}
```
- Curl:
```
curl -X POST https://freshbackend-production-096a.up.railway.app/api/detection/batch-fruit \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer YOUR_JWT_TOKEN" \
	-d '{"image_ids":["3fa85f64-5717-4562-b3fc-2c963f66afa6","4fb95f64-5817-4662-b4fc-3d963f77bfb7"]}'
```

### GET /api/detection/fruit/{detection_id}
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Path parameter `detection_id=5fc96f74-5927-4772-b5fc-4e074f88cgc8`
- Sample Output:
```json
{
	"detection_id": "5fc96f74-5927-4772-b5fc-4e074f88cgc8",
	"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"image_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"fruit_type": "orange",
	"confidence": 0.95,
	"bounding_box": {
		"x": 100.0,
		"y": 100.0,
		"width": 200.0,
		"height": 200.0
	},
	"created_at": "2025-10-05T12:35:30.789Z"
}
```
- Curl:
```
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
	https://freshbackend-production-096a.up.railway.app/api/detection/fruit/5fc96f74-5927-4772-b5fc-4e074f88cgc8
```

### GET /api/detection/fruit/results
- **Authentication Required**: Yes (Bearer token)
- Sample Input: Query parameters `limit=10&offset=0` (user_id comes from authentication)
- Sample Output:
```json
[
	{
		"detection_id": "5fc96f74-5927-4772-b5fc-4e074f88cgc8",
		"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"image_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"fruit_type": "orange",
		"confidence": 0.95,
		"bounding_box": {
			"x": 100.0,
			"y": 100.0,
			"width": 200.0,
			"height": 200.0
		},
		"created_at": "2025-10-05T12:35:30.789Z"
	},
	{
		"detection_id": "6gd07g85-6037-4883-c6gd-5f185g99dhd9",
		"user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
		"image_id": "4fb95f64-5817-4662-b4fc-3d963f77bfb7",
		"fruit_type": "orange",
		"confidence": 0.95,
		"bounding_box": {
			"x": 100.0,
			"y": 100.0,
			"width": 200.0,
			"height": 200.0
		},
		"created_at": "2025-10-05T12:35:31.123Z"
	}
]
```
- Curl:
```
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
	"https://freshbackend-production-096a.up.railway.app/api/detection/fruit/results?limit=10&offset=0"
```

## Authentication Flow

To use the protected endpoints, you need to:

1. **Sign up** or **Log in** to get a JWT token:
```bash
# Login to get token
curl -X POST https://freshbackend-production-096a.up.railway.app/api/auth/login \
	-H "Content-Type: application/json" \
	-d '{"email":"your@email.com","password":"yourpassword"}'
```

2. **Use the token** from the response in subsequent requests:
```bash
# Example response from login
{
	"id": "user-uuid",
	"email": "your@email.com",
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
	"token_type": "bearer"
}
```

3. **Include the token** in the Authorization header for protected endpoints:
```bash
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
