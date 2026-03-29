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
    allowed_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,https://fresh-web-desktop-gsmg.vercel.app,https://freshbackend-production-096a.up.railway.app", 
        alias="ALLOWED_ORIGINS"
    )
    
    # File Upload Configuration
    max_file_size: int = 10485760  # 10MB default
    allowed_file_types_str: str = Field(default="image/jpeg,image/png,image/webp", alias="ALLOWED_FILE_TYPES")
    
    # Google OAuth Configuration
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    
    # ML API Configuration
    ml_api_url: str = Field(default="http://localhost:8000", alias="ML_API_URL")
    ml_api_timeout: int = Field(default=300, alias="ML_API_TIMEOUT")  # 5 minutes for ML processing
    ml_api_max_retries: int = Field(default=3, alias="ML_API_MAX_RETRIES")
    
    # Weather API Configuration
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    weather_cache_ttl_minutes: int = Field(default=30, alias="WEATHER_CACHE_TTL_MINUTES")
    weather_update_interval_minutes: int = Field(default=30, alias="WEATHER_UPDATE_INTERVAL_MINUTES")
    weather_forecast_days: int = Field(default=5, alias="WEATHER_FORECAST_DAYS")
    
    # Email Configuration
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="FRESH - Fruit Disease Alert System", alias="SMTP_FROM_NAME")
    email_enabled: bool = Field(default=True, alias="EMAIL_ENABLED")
    email_send_alerts: bool = Field(default=True, alias="EMAIL_SEND_ALERTS")
    
    # AI Assistant Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    
    # Application Info
    app_name: str = "FRESH Backend API"
    app_version: str = "1.0.0"
    
    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from string to list."""
        # Handle wildcard case - return comprehensive list instead of ["*"]
        if self.allowed_origins_str.strip() == "*":
            # Return comprehensive list of likely origins instead of wildcard
            comprehensive_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:3002",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8080",
                "https://localhost:3000",
                "https://127.0.0.1:3000",
                "https://monkfish-app-vgy3w.ondigitalocean.app",  # Your frontend
                "https://clownfish-app-wyp5e.ondigitalocean.app",  # Your backend
                # Add common domains that might be used
                "https://fresh-web-desktop-gsmg.vercel.app",
                "https://freshbackend-production-096a.up.railway.app"
            ]
            print(f"🔧 CORS Wildcard detected - using comprehensive origins: {comprehensive_origins}")
            return comprehensive_origins
        
        # Parse comma-separated origins
        origins = [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]
        
        # Add DigitalOcean origins if not present
        required_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://monkfish-app-vgy3w.ondigitalocean.app",  # Your frontend
            "https://clownfish-app-wyp5e.ondigitalocean.app"   # Your backend
        ]
        
        for required_origin in required_origins:
            if required_origin not in origins:
                origins.append(required_origin)
        
        print(f"🔧 CORS Allowed Origins: {origins}")
        return origins
    
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


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings