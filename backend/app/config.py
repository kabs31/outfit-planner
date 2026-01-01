"""
Configuration for AI Outfit Recommender
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App Config
    APP_NAME: str = "AI Outfit Recommender"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Config
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Groq LLM (Free tier)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    # Replicate API (Virtual Try-On)
    REPLICATE_API_TOKEN: str = ""
    
    # Cloudinary (Image Storage)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # RapidAPI (ASOS Products)
    RAPIDAPI_KEY: str = ""
    
    # CORS Origins
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "https://your-app.vercel.app"  # Update for production
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Sentry (Error Monitoring - Optional)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Default Model Image (for virtual try-on)
    MODEL_IMAGE_URL: str = "https://i.pinimg.com/1200x/17/cd/c1/17cdc121e45e69310685422a7f1455a2.jpg"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Global settings instance
settings = Settings()


def get_cors_origins() -> list:
    """Get CORS origins"""
    return settings.CORS_ORIGINS
