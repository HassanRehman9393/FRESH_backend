from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    
    # Application Configuration
    debug: bool = False
    secret_key: str = "fallback-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # CORS Configuration - use Field with alias to map environment variable
    allowed_origins_str: str = Field(default="http://localhost:3000,http://localhost:3001,https://your-frontend-domain.com", alias="ALLOWED_ORIGINS")
    
    # File Upload Configuration
    max_file_size: int = 10485760  # 10MB default
    allowed_file_types_str: str = Field(default="image/jpeg,image/png,image/webp", alias="ALLOWED_FILE_TYPES")
    
    # Application Info
    app_name: str = "FRESH Backend API"
    app_version: str = "1.0.0"
    
    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from string to list."""
        # Never return ["*"] when using credentials
        origins = [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]
        # Filter out "*" if present when using credentials
        filtered_origins = [origin for origin in origins if origin != "*"]
        
        # Add common development origins if not present
        dev_origins = ["http://localhost:3000", "http://localhost:3001"]
        for dev_origin in dev_origins:
            if dev_origin not in filtered_origins:
                filtered_origins.append(dev_origin)
        
        print(f"🔧 CORS Allowed Origins: {filtered_origins}")
        return filtered_origins
    
    @property
    def allowed_file_types(self) -> List[str]:
        """Parse allowed file types from string to list."""
        return [file_type.strip() for file_type in self.allowed_file_types_str.split(",") if file_type.strip()]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'  # Ignore extra environment variables
    )

# Create settings instance
settings = Settings()