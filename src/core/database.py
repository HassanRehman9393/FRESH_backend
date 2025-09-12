from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from supabase import create_client, Client
import asyncio
from typing import AsyncGenerator, Optional
from .config import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy setup for Supabase PostgreSQL
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    echo=settings.debug,  # Enable SQL logging in debug mode
    pool_pre_ping=True,  # Verify connections before use
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Metadata for table reflection
metadata = MetaData()

# Supabase client instance
supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    """
    global supabase_client
    if supabase_client is None:
        try:
            supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    return supabase_client

# Dependency to get database session
def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database health check using Supabase client
def check_database_health() -> bool:
    """
    Check if database connection is healthy using Supabase client.
    Returns True if connection is successful, False otherwise.
    """
    try:
        client = get_supabase_client()
        
        # Simple test query - try to select from a system table or create a test table
        result = client.table("information_schema.tables").select("table_name").limit(1).execute()
        
        # If we can execute the query, the connection is healthy
        logger.info("Supabase connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False

# Async wrapper for health check
async def check_database_health_async() -> bool:
    """
    Async wrapper for database health check.
    """
    return check_database_health()

# Initialize database (for future migrations)
def init_db():
    """
    Initialize database tables.
    This will be used when we add SQLAlchemy models.
    """
    # Import all models here to ensure they are registered with SQLAlchemy
    # from ..models import user, detection, disease, image, result
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")