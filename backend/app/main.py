"""
Main FastAPI Application for AI Outfit Recommender
Complete API with all endpoints
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import time
import uuid
from datetime import datetime
import logging
from typing import List

from app.config import settings, get_cors_origins, validate_settings
from app.database import get_db, init_db, check_db_connection, Product, GeneratedOutfit as DBOutfit, UserFeedback as DBFeedback, SearchQuery as DBSearchQuery
from app.models import (
    OutfitPromptRequest,
    OutfitResponse,
    GeneratedOutfit,
    UserFeedbackRequest,
    HealthCheck,
    ErrorResponse
)
from app.services.llama_service import llama_service
from app.services.product_service import product_service
from app.services.tryon_service import tryon_service

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered outfit recommendation with virtual try-on",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # Validate configuration
    validate_settings()
    
    # Initialize database
    try:
        init_db()
        if check_db_connection():
            logger.info("✅ Database connected")
        else:
            logger.warning("⚠️  Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Check services
    llama_health = llama_service.health_check()
    logger.info(f"Llama service: {llama_health['status']}")
    
    logger.info("=" * 60)
    logger.info("✅ Application startup complete")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down application...")


# ==================== HEALTH CHECK ====================

@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Check system health"""
    services = {}
    
    # Check database
    if check_db_connection():
        services["database"] = "connected"
    else:
        services["database"] = "disconnected"
    
    # Check Llama
    llama_health = llama_service.health_check()
    services["llama"] = llama_health["status"]
    
    # Check RunPod (optional)
    if settings.RUNPOD_API_KEY:
        services["runpod"] = "configured"
    else:
        services["runpod"] = "not_configured"
    
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services
    )


# ==================== OUTFIT GENERATION ====================

@app.post(
    f"{settings.API_PREFIX}/outfits/generate",
    response_model=OutfitResponse,
    tags=["Outfits"],
    summary="Generate outfit recommendations from prompt"
)
async def generate_outfits(
    request: OutfitPromptRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    use_local: bool = False  # For development testing
):
    """
    Generate AI-powered outfit recommendations
    
    - **prompt**: Natural language description (e.g., "Beach party, colorful relaxed")
    - **max_price**: Optional maximum total price filter
    - **preferred_brands**: Optional list of preferred brands
    - **exclude_categories**: Optional categories to exclude
    
    Returns list of outfit combinations with virtual try-on images.
    """
    start_time = time.time()
    
    try:
        logger.info(f"📝 Processing prompt: {request.prompt}")
        
        # Step 1: Parse prompt with Llama
        parsed_prompt = llama_service.parse_outfit_prompt(request.prompt)
        logger.info(f"✅ Parsed: {parsed_prompt.dict()}")
        
        # Step 2: Find matching outfit combinations
        outfit_combinations = product_service.find_matching_outfits(
            db=db,
            parsed_prompt=parsed_prompt,
            max_price=request.max_price,
            num_outfits=3  # Generate 3 outfits
        )
        
        if not outfit_combinations:
            raise HTTPException(
                status_code=404,
                detail="No matching outfits found for your prompt. Try different keywords."
            )
        
        logger.info(f"✅ Found {len(outfit_combinations)} outfit combinations")
        
        # Step 3: Generate virtual try-on images
        logger.info("🎨 Generating try-on images...")
        tryon_urls = await tryon_service.generate_multiple_outfits(
            outfit_combinations,
            use_local=use_local
        )
        
        # Step 4: Create response with generated outfits
        generated_outfits = []
        
        for i, (combo, tryon_url) in enumerate(zip(outfit_combinations, tryon_urls)):
            if tryon_url is None:
                logger.warning(f"Skipping outfit {i+1} - image generation failed")
                continue
            
            outfit_id = f"outfit_{uuid.uuid4().hex[:12]}"
            
            generated_outfit = GeneratedOutfit(
                outfit_id=outfit_id,
                combination=combo,
                tryon_image_url=tryon_url,
                prompt=request.prompt,
                generated_at=datetime.utcnow()
            )
            
            generated_outfits.append(generated_outfit)
            
            # Save to database in background
            background_tasks.add_task(
                save_generated_outfit,
                db=db,
                outfit_id=outfit_id,
                combo=combo,
                tryon_url=tryon_url,
                prompt=request.prompt,
                parsed_prompt=parsed_prompt
            )
        
        if not generated_outfits:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate outfit images. Please try again."
            )
        
        processing_time = time.time() - start_time
        
        # Log search query
        background_tasks.add_task(
            log_search_query,
            db=db,
            query=request.prompt,
            parsed_data=parsed_prompt.dict(),
            results_count=len(generated_outfits),
            processing_time=processing_time
        )
        
        logger.info(f"✅ Generated {len(generated_outfits)} outfits in {processing_time:.2f}s")
        
        return OutfitResponse(
            success=True,
            message=f"Generated {len(generated_outfits)} outfit recommendations",
            outfits=generated_outfits,
            total_count=len(generated_outfits),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating outfits: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ==================== USER FEEDBACK ====================

@app.post(
    f"{settings.API_PREFIX}/outfits/feedback",
    tags=["Outfits"],
    summary="Record user feedback on outfit"
)
async def submit_feedback(
    request: UserFeedbackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Record user feedback (like/dislike/skip) on outfit
    
    - **outfit_id**: ID of the outfit
    - **action**: User action (like/dislike/skip)
    - **user_id**: Optional user ID for tracking
    """
    try:
        # Save feedback in background
        background_tasks.add_task(
            save_user_feedback,
            db=db,
            outfit_id=request.outfit_id,
            action=request.action.value,
            user_id=request.user_id
        )
        
        return {"success": True, "message": "Feedback recorded"}
        
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PRODUCT SYNC ====================

@app.post(
    f"{settings.API_PREFIX}/products/sync",
    tags=["Products"],
    summary="Sync products from external APIs"
)
async def sync_products(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Fetch and sync products from external APIs to database
    This should be run periodically to update product catalog
    """
    try:
        count = await product_service.sync_products_to_db(db)
        return {
            "success": True,
            "message": f"Synced {count} products",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error syncing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    f"{settings.API_PREFIX}/products/count",
    tags=["Products"],
    summary="Get product count"
)
async def get_product_count(db: Session = Depends(get_db)):
    """Get total number of products in database"""
    count = db.query(Product).filter(Product.is_active == True).count()
    return {"count": count}


# ==================== BACKGROUND TASKS ====================

def save_generated_outfit(
    db: Session,
    outfit_id: str,
    combo,
    tryon_url: str,
    prompt: str,
    parsed_prompt
):
    """Save generated outfit to database"""
    try:
        db_outfit = DBOutfit(
            outfit_id=outfit_id,
            top_id=combo.top.id,
            bottom_id=combo.bottom.id,
            tryon_image_url=tryon_url,
            original_prompt=prompt,
            parsed_prompt=parsed_prompt.dict() if parsed_prompt else None,
            total_price=combo.total_price,
            match_score=combo.match_score,
            style_tags=combo.style_tags
        )
        db.add(db_outfit)
        db.commit()
        logger.info(f"✅ Saved outfit {outfit_id} to database")
    except Exception as e:
        logger.error(f"Failed to save outfit: {e}")
        db.rollback()


def save_user_feedback(
    db: Session,
    outfit_id: str,
    action: str,
    user_id: str = None
):
    """Save user feedback to database"""
    try:
        feedback = DBFeedback(
            outfit_id=outfit_id,
            user_id=user_id,
            action=action
        )
        db.add(feedback)
        
        # Update outfit statistics
        outfit = db.query(DBOutfit).filter(DBOutfit.outfit_id == outfit_id).first()
        if outfit:
            if action == "like":
                outfit.like_count += 1
            elif action == "dislike":
                outfit.dislike_count += 1
        
        db.commit()
        logger.info(f"✅ Saved feedback for outfit {outfit_id}")
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        db.rollback()


def log_search_query(
    db: Session,
    query: str,
    parsed_data: dict,
    results_count: int,
    processing_time: float
):
    """Log search query for analytics"""
    try:
        search_log = DBSearchQuery(
            query=query,
            parsed_data=parsed_data,
            results_count=results_count,
            processing_time=processing_time
        )
        db.add(search_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log search query: {e}")
        db.rollback()


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# ==================== ROOT ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
