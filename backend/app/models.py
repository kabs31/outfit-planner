"""
Data models for AI Outfit App
Pydantic models for API requests/responses and SQLAlchemy models for database
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class ClothingCategory(str, Enum):
    """Clothing categories"""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    SHOES = "shoes"
    ACCESSORIES = "accessories"


class OutfitMood(str, Enum):
    """Outfit moods"""
    CASUAL = "casual"
    FORMAL = "formal"
    PARTY = "party"
    SPORT = "sport"
    BEACH = "beach"
    BUSINESS = "business"


class UserAction(str, Enum):
    """User actions on outfits"""
    LIKE = "like"
    DISLIKE = "dislike"
    SKIP = "skip"


# ==================== REQUEST MODELS ====================

class OutfitPromptRequest(BaseModel):
    """Request model for outfit generation from prompt"""
    prompt: str = Field(..., min_length=3, max_length=500, description="User's outfit prompt")
    
    # Optional filters
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    preferred_brands: Optional[List[str]] = Field(None, description="List of preferred brands")
    exclude_categories: Optional[List[ClothingCategory]] = Field(None, description="Categories to exclude")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Beach party, colorful and relaxed",
                "max_price": 5000,
                "preferred_brands": ["Zara", "H&M"]
            }
        }


class UserFeedbackRequest(BaseModel):
    """Request model for user feedback on outfit"""
    outfit_id: str = Field(..., description="Unique outfit ID")
    action: UserAction = Field(..., description="User action: like/dislike/skip")
    user_id: Optional[str] = Field(None, description="Optional user ID for tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "outfit_id": "outfit_123456",
                "action": "like",
                "user_id": "user_789"
            }
        }


# ==================== RESPONSE MODELS ====================

class ProductItem(BaseModel):
    """Individual product item"""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    category: ClothingCategory = Field(..., description="Product category")
    price: float = Field(..., ge=0, description="Product price")
    currency: str = Field(default="INR", description="Currency code")
    image_url: HttpUrl = Field(..., description="Product image URL")
    buy_url: HttpUrl = Field(..., description="Purchase URL")
    brand: Optional[str] = Field(None, description="Brand name")
    description: Optional[str] = Field(None, description="Product description")
    colors: Optional[List[str]] = Field(None, description="Available colors")
    sizes: Optional[List[str]] = Field(None, description="Available sizes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "prod_123",
                "name": "Floral Beach Shirt",
                "category": "top",
                "price": 1299.00,
                "currency": "INR",
                "image_url": "https://example.com/shirt.jpg",
                "buy_url": "https://example.com/buy/shirt",
                "brand": "Zara",
                "colors": ["blue", "white"],
                "sizes": ["S", "M", "L"]
            }
        }


class OutfitCombination(BaseModel):
    """Outfit combination (top + bottom)"""
    top: ProductItem
    bottom: ProductItem
    total_price: float = Field(..., ge=0, description="Combined price")
    match_score: float = Field(..., ge=0, le=1, description="How well items match (0-1)")
    style_tags: List[str] = Field(default_factory=list, description="Style tags")


class GeneratedOutfit(BaseModel):
    """Complete generated outfit with try-on image"""
    outfit_id: str = Field(..., description="Unique outfit ID")
    combination: OutfitCombination
    tryon_image_url: HttpUrl = Field(..., description="Generated try-on image URL")
    prompt: str = Field(..., description="Original user prompt")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "outfit_id": "outfit_abc123",
                "combination": {
                    "top": {"id": "top_1", "name": "Beach Shirt", "category": "top", "price": 1299, "image_url": "...", "buy_url": "..."},
                    "bottom": {"id": "bottom_1", "name": "Shorts", "category": "bottom", "price": 899, "image_url": "...", "buy_url": "..."},
                    "total_price": 2198,
                    "match_score": 0.92,
                    "style_tags": ["casual", "beach", "summer"]
                },
                "tryon_image_url": "https://cloudinary.com/outfit_abc123.jpg",
                "prompt": "Beach party, colorful relaxed",
                "generated_at": "2024-01-15T10:30:00"
            }
        }


class OutfitResponse(BaseModel):
    """API response with generated outfits"""
    success: bool = Field(default=True)
    message: str = Field(default="Outfits generated successfully")
    outfits: List[GeneratedOutfit]
    total_count: int = Field(..., ge=0)
    processing_time: float = Field(..., ge=0, description="Time taken in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Generated 3 outfits",
                "outfits": [],
                "total_count": 3,
                "processing_time": 5.2
            }
        }


# ==================== INTERNAL MODELS ====================

class ParsedPrompt(BaseModel):
    """Parsed user prompt with extracted attributes"""
    original_prompt: str
    mood: Optional[str] = None
    location: Optional[str] = None
    occasion: Optional[str] = None
    style: Optional[str] = None
    colors: List[str] = Field(default_factory=list)
    season: Optional[str] = None
    formality: Optional[str] = None  # casual, formal, semi-formal
    
    # Extracted filters
    keywords: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_prompt": "Beach party, colorful relaxed",
                "mood": "relaxed",
                "location": "beach",
                "occasion": "party",
                "style": "casual",
                "colors": ["colorful", "bright"],
                "season": "summer",
                "formality": "casual",
                "keywords": ["beach", "party", "colorful", "relaxed"]
            }
        }


class ProductEmbedding(BaseModel):
    """Product with embedding vector"""
    product: ProductItem
    embedding: List[float] = Field(..., description="384-dim vector")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== ERROR MODELS ====================

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error info")
    error_code: Optional[str] = Field(None, description="Error code for debugging")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Failed to generate outfit",
                "detail": "No matching products found for prompt",
                "error_code": "NO_MATCHES"
            }
        }


# ==================== HEALTH CHECK ====================

class HealthCheck(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy")
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00",
                "services": {
                    "database": "connected",
                    "llama": "running",
                    "runpod": "available"
                }
            }
        }
