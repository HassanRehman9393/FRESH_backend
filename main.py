from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
from src.api import auth_router
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )