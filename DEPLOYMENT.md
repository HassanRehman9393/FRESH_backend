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
