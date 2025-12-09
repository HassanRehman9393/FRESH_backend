from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from src.core.config import settings
from src.core.database import check_database_health_async, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup events
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    
    # Log ML API configuration
    print(f"🤖 ML API URL: {settings.ml_api_url}")
    print(f"⏱️  ML API Timeout: {settings.ml_api_timeout}s")
    
    # Warn if ML API URL is localhost in production
    if not settings.debug and "localhost" in settings.ml_api_url.lower():
        print("⚠️  WARNING: ML_API_URL is set to localhost but DEBUG=False")
        print("💡 Set ML_API_URL environment variable to your deployed ML API URL")
    
    # Check database connectivity (non-blocking)
    try:
        db_healthy = await check_database_health_async()
        if db_healthy:
            print("✅ Database connection successful")
        else:
            print("⚠️ Database connection failed - API will start without database")
            print("💡 You can test database connectivity using /health endpoint")
    except Exception as e:
        print(f"⚠️ Database check error: {e}")
        print("💡 API starting without database verification")
    
    # Initialize database tables (for future use)
    # init_db()
    
    yield
    
    # Shutdown events
    print("🛑 Shutting down application")


# Create FastAPI application instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for FRESH - Fruit Recognition and Evaluation System for Health",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    print(f"📥 [{request.method}] {request.url.path} - Origin: {request.headers.get('origin', 'N/A')}")
    response = await call_next(request)
    print(f"📤 [{request.method}] {request.url.path} - Status: {response.status_code}")
    return response

# Add CORS middleware - Use settings-based origins for DigitalOcean deployment
print("🔧 Configuring CORS for DigitalOcean deployment")

# Add comprehensive CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Use dynamic origins from settings
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Custom exception handler to ensure CORS headers are always sent
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors and ensure CORS headers are sent."""
    origin = request.headers.get("origin", "")
    
    # Check if origin is allowed
    if origin in settings.allowed_origins:
        allowed_origin = origin
    else:
        allowed_origin = "https://monkfish-app-vgy3w.ondigitalocean.app"  # Fallback to frontend
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Custom exception handler for all HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and ensure CORS headers are sent."""
    origin = request.headers.get("origin", "")
    
    # Check if origin is allowed
    if origin in settings.allowed_origins:
        allowed_origin = origin
    else:
        allowed_origin = "https://monkfish-app-vgy3w.ondigitalocean.app"  # Fallback to frontend
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Manual OPTIONS handler for preflight requests (additional safety)
@app.options("/{full_path:path}")
async def options_handler(full_path: str, request: Request):
    """Handle preflight OPTIONS requests manually for extra CORS compatibility."""
    # Get the origin from the request header
    origin = request.headers.get("origin", "https://monkfish-app-vgy3w.ondigitalocean.app")
    
    # Debug logging
    print(f"🔧 OPTIONS Request - Origin: {origin}, Path: {full_path}")
    print(f"🔧 Request Headers: {dict(request.headers)}")
    
    # Check if origin is in allowed origins
    if origin in settings.allowed_origins or "*" in settings.allowed_origins:
        allowed_origin = origin
    else:
        allowed_origin = "https://monkfish-app-vgy3w.ondigitalocean.app"  # Default to your frontend
    
    print(f"🔧 Responding with Origin: {allowed_origin}")
    
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, Origin, Access-Control-Request-Method, Access-Control-Request-Headers",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API and database connectivity.
    """
    db_healthy = await check_database_health_async()
    
    return JSONResponse(
        status_code=200 if db_healthy else 503,
        content={
            "status": "healthy" if db_healthy else "unhealthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "database": "connected" if db_healthy else "disconnected",
        }
    )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# Import and include API routers
from src.api import (
    auth_router, 
    images_router, 
    detection_router, 
    disease_router,
    orchards_router,
    weather_router,
    alerts_router,
    weather_risk_router
)
app.include_router(auth_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(detection_router, prefix="/api")
app.include_router(disease_router, prefix="/api")
app.include_router(orchards_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(weather_risk_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )