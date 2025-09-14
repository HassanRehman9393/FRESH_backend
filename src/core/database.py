from supabase import create_client, Client
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    """
    return supabase

# Database health check using Supabase client
def check_database_health() -> bool:
    """
    Check if database connection is healthy using Supabase client.
    Returns True if connection is successful, False otherwise.
    """
    try:
        # Simple connection test - just check if we can access the auth endpoint
        # This doesn't require any tables to exist
        result = supabase.auth.get_session()
        
        # If we can execute the auth check, the connection is healthy
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

# Initialize database (for future use)
def init_db():
    """
    Initialize database or perform startup tasks.
    """
    try:
        # Test the connection
        if check_database_health():
            logger.info("Database initialization completed successfully")
        else:
            logger.warning("Database initialization - connection test failed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print("Database initialization failed, but application will continue")