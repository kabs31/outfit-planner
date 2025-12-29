"""
Configuration management for AI Outfit App
Handles all environment variables and settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Config
    APP_NAME: str = "AI Outfit Recommender"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Config
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/outfit_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Ollama/Llama Config
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b-q4_0"  # 4-bit quantized for 8GB GPU
    
    # RunPod GPU API
    RUNPOD_API_KEY: str = ""
    RUNPOD_ENDPOINT_ID: str = ""  # Your IDM-VTON endpoint
    
    # Cloudinary (Image Storage)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # Product APIs
    FAKE_STORE_API: str = "https://fakestoreapi.com"
    # Add more as you integrate: Amazon, Flipkart, etc.
    
    # Embedding Model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384  # Dimension for MiniLM
    
    # Redis (Optional - for caching)
    REDIS_URL: Optional[str] = None
    REDIS_TTL: int = 3600  # 1 hour cache
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "https://your-app.vercel.app"  # Your production URL
    ]
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}
    
    # Virtual Try-On Settings
    TRYON_IMAGE_SIZE: tuple = (512, 768)  # Width x Height
    TRYON_STEPS: int = 30  # Inference steps (lower = faster but less quality)
    TRYON_GUIDANCE_SCALE: float = 7.5
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Model Base Image (for virtual try-on)
    MODEL_IMAGE_URL: str = "https://example.com/model-base.jpg"  # Replace with your model photo
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()


# Helper function to validate settings on startup
def validate_settings():
    """Validate critical settings are configured"""
    errors = []
    
    if not settings.DATABASE_URL or settings.DATABASE_URL == "postgresql://user:password@localhost:5432/outfit_db":
        errors.append("DATABASE_URL not configured")
    
    if not settings.RUNPOD_API_KEY:
        errors.append("RUNPOD_API_KEY not configured")
    
    if not settings.CLOUDINARY_CLOUD_NAME:
        errors.append("Cloudinary credentials not configured")
    
    if errors:
        print("⚠️  WARNING: Configuration issues detected:")
        for error in errors:
            print(f"  - {error}")
        print("\n💡 These will work in development but are required for production")
    else:
        print("✅ All critical settings configured")


# Environment-specific configs
def get_database_url() -> str:
    """Get database URL with fallback"""
    return settings.DATABASE_URL


def is_production() -> bool:
    """Check if running in production"""
    return not settings.DEBUG and "railway" in settings.DATABASE_URL.lower()


def get_cors_origins() -> list:
    """Get CORS origins based on environment"""
    if is_production():
        return [origin for origin in settings.CORS_ORIGINS if "localhost" not in origin]
    return settings.CORS_ORIGINS
