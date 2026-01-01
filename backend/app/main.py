"""
AI Outfit Recommender - FastAPI Application
Simplified version without PostgreSQL database
"""
from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import time
import uuid
from datetime import datetime
import logging
import io

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Cloudinary
import cloudinary
import cloudinary.uploader

# App imports
from app.config import settings, get_cors_origins
from app.models import (
    OutfitPromptRequest,
    OutfitResponse,
    GeneratedOutfit,
    HealthCheck,
    ProductItem,
)
from app.services.llm_service import llm_service
from app.services.product_service import product_service
from app.services.tryon_service import tryon_service
from app.services.asos_service import asos_service
from app.services.amazon_service import amazon_service
from app.services.firebase_auth import verify_firebase_token, get_user_id_from_token
from app.services.usage_tracker import get_user_usage, increment_search, increment_tryon, get_admin_stats, get_global_usage

# Sentry Error Monitoring (optional)
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[FastApiIntegration(transaction_style="endpoint")],
        debug=settings.DEBUG,
        send_default_pii=False,
    )

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered outfit recommendation with virtual try-on",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    logger.info(f"LLM service: configured={llm_service.is_configured}")
    logger.info(f"ASOS API: {'configured' if settings.RAPIDAPI_KEY else 'not configured'}")
    logger.info(f"Amazon API: {'configured' if settings.RAPIDAPI_KEY else 'not configured'}")
    logger.info(f"Cloudinary: {'configured' if settings.CLOUDINARY_CLOUD_NAME else 'not configured'}")
    logger.info(f"Replicate: {'configured' if settings.REPLICATE_API_TOKEN else 'not configured'}")
    logger.info("=" * 60)
    logger.info("✅ Application startup complete")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down application...")


# ==================== HEALTH CHECK ====================

@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Check system health"""
    services = {}
    
    # Check LLM (Groq)
    llm_health = await llm_service.health_check()
    services["llm"] = llm_health.get("status", "unknown")
    
    # Check APIs
    services["asos"] = "configured" if settings.RAPIDAPI_KEY else "not_configured"
    services["amazon"] = "configured" if settings.RAPIDAPI_KEY else "not_configured"
    services["cloudinary"] = "configured" if settings.CLOUDINARY_CLOUD_NAME else "not_configured"
    services["replicate"] = "configured" if settings.REPLICATE_API_TOKEN else "not_configured"
    
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services
    )


# ==================== HELPER: GET FIREBASE USER ====================

async def get_firebase_user(request: Request) -> Optional[str]:
    """Get Firebase user ID from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = await verify_firebase_token(token)
        if payload:
            return get_user_id_from_token(payload)
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
    
    return None


# ==================== BROWSE OUTFITS (ASOS) ====================

@app.post(
    f"{settings.API_PREFIX}/outfits/browse-asos",
    response_model=OutfitResponse,
    tags=["Outfits"],
    summary="Browse outfits from ASOS"
)
@limiter.limit("20/minute")
async def browse_outfits_asos(request: Request, prompt_request: OutfitPromptRequest):
    """
    Browse outfit combinations from ASOS
    
    - Requires Google sign-in
    - Limited to 2 searches per 5 days
    - Returns 3 outfit combinations per search
    """
    start_time = time.time()
    
    try:
        # Check authentication
        user_id = await get_firebase_user(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Please sign in with Google to browse outfits."
            )
        
        # Check usage limits (per-user AND global)
        usage = get_user_usage(user_id)
        if not usage["can_search"]:
            if usage["search_exhausted"]:
                raise HTTPException(
                    status_code=429,
                    detail="You've already used your 1 free search. Thank you for trying our app!"
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Sorry, we've reached our search limit. Please try again later."
                )
        
        # Increment usage (user + global)
        if not increment_search(user_id):
            raise HTTPException(status_code=429, detail="Unable to process. Please try again.")
        
        gender = prompt_request.gender or "women"
        logger.info(f"🛍️ Browsing for user {user_id[:8]}...: {prompt_request.prompt}")
        
        if not settings.RAPIDAPI_KEY:
            raise HTTPException(status_code=503, detail="ASOS API not configured")
        
        # Parse prompt with LLM
        parsed_prompt = await llm_service.parse_outfit_prompt(prompt_request.prompt)
        logger.info(f"✅ Parsed: {parsed_prompt.dict()}")
        
        # Fetch from ASOS
        asos_result = await asos_service.browse_fashion(
            prompt=prompt_request.prompt,
            num_tops=5,
            num_bottoms=5,
            gender=gender
        )
        
        tops = asos_result["tops"]
        bottoms = asos_result["bottoms"]
        
        if not tops or not bottoms:
            raise HTTPException(status_code=404, detail="No matching products found")
        
        # Create product items
        top_items = [
            ProductItem(
                id=t["id"], name=t["name"], category="top",
                price=t["price"], currency=t["currency"],
                image_url=t["image_url"], buy_url=t["buy_url"],
                brand=t["brand"], description=t.get("description", ""),
            )
            for t in tops
        ]
        
        bottom_items = [
            ProductItem(
                id=b["id"], name=b["name"], category="bottom",
                price=b["price"], currency=b["currency"],
                image_url=b["image_url"], buy_url=b["buy_url"],
                brand=b["brand"], description=b.get("description", ""),
            )
            for b in bottoms
        ]
        
        # Create combinations (max 3)
        outfit_combinations = product_service.create_outfit_combinations(
            tops=top_items,
            bottoms=bottom_items,
            max_combinations=3
        )
        
        # Build response
        generated_outfits = [
            GeneratedOutfit(
                outfit_id=f"asos_{uuid.uuid4().hex[:8]}",
                prompt=prompt_request.prompt,
                combination=combo,
                tryon_image_url=None,
                created_at=datetime.now()
            )
            for combo in outfit_combinations
        ]
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Found {len(generated_outfits)} outfits in {processing_time:.2f}s")
        
        return OutfitResponse(
            success=True,
            message=f"Found {len(generated_outfits)} outfits",
            outfits=generated_outfits,
            total_count=len(generated_outfits),
            processing_time=processing_time,
            parsed_prompt=parsed_prompt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BROWSE OUTFITS (AMAZON) ====================

@app.post(
    f"{settings.API_PREFIX}/outfits/browse-amazon",
    response_model=OutfitResponse,
    tags=["Outfits"],
    summary="Browse outfits from Amazon"
)
@limiter.limit("20/minute")
async def browse_outfits_amazon(request: Request, prompt_request: OutfitPromptRequest):
    """
    Browse outfit combinations from Amazon
    
    - Requires Google sign-in
    - Limited to 1 search per user (lifetime)
    - Returns 3 outfit combinations per search
    """
    start_time = time.time()
    
    try:
        # Check authentication
        user_id = await get_firebase_user(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Please sign in with Google to browse outfits."
            )
        
        # Check usage limits (per-user AND global)
        usage = get_user_usage(user_id)
        if not usage["can_search"]:
            if usage["search_exhausted"]:
                raise HTTPException(
                    status_code=429,
                    detail="You've already used your 1 free search. Thank you for trying our app!"
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Sorry, we've reached our search limit. Please try again later."
                )
        
        # Increment usage (user + global)
        if not increment_search(user_id):
            raise HTTPException(status_code=429, detail="Unable to process. Please try again.")
        
        gender = prompt_request.gender or "women"
        logger.info(f"🛒 Amazon browse for user {user_id[:8]}...: {prompt_request.prompt}")
        
        if not settings.RAPIDAPI_KEY:
            raise HTTPException(status_code=503, detail="Amazon API not configured")
        
        # Parse prompt with LLM
        parsed_prompt = await llm_service.parse_outfit_prompt(prompt_request.prompt)
        logger.info(f"✅ Parsed: {parsed_prompt.dict()}")
        
        # Fetch from Amazon
        amazon_result = await amazon_service.browse_fashion(
            prompt=prompt_request.prompt,
            num_tops=5,
            num_bottoms=5,
            gender=gender
        )
        
        tops = amazon_result["tops"]
        bottoms = amazon_result["bottoms"]
        
        if not tops or not bottoms:
            raise HTTPException(status_code=404, detail="No matching products found on Amazon")
        
        # Create product items
        top_items = [
            ProductItem(
                id=t["id"], name=t["name"], category="top",
                price=t["price"], currency=t["currency"],
                image_url=t["image_url"], buy_url=t["buy_url"],
                brand=t["brand"], description=t.get("description", ""),
            )
            for t in tops
        ]
        
        bottom_items = [
            ProductItem(
                id=b["id"], name=b["name"], category="bottom",
                price=b["price"], currency=b["currency"],
                image_url=b["image_url"], buy_url=b["buy_url"],
                brand=b["brand"], description=b.get("description", ""),
            )
            for b in bottoms
        ]
        
        # Create combinations (max 3)
        outfit_combinations = product_service.create_outfit_combinations(
            tops=top_items,
            bottoms=bottom_items,
            max_combinations=3
        )
        
        # Build response
        generated_outfits = [
            GeneratedOutfit(
                outfit_id=f"amz_{uuid.uuid4().hex[:8]}",
                prompt=prompt_request.prompt,
                combination=combo,
                tryon_image_url=None,
                created_at=datetime.now()
            )
            for combo in outfit_combinations
        ]
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Found {len(generated_outfits)} Amazon outfits in {processing_time:.2f}s")
        
        return OutfitResponse(
            success=True,
            message=f"Found {len(generated_outfits)} Amazon outfits",
            outfits=generated_outfits,
            total_count=len(generated_outfits),
            processing_time=processing_time,
            parsed_prompt=parsed_prompt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Amazon Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BROWSE OUTFITS (MIXED STORES) ====================

@app.post(
    f"{settings.API_PREFIX}/outfits/browse-mixed",
    response_model=OutfitResponse,
    tags=["Outfits"],
    summary="Browse outfits from multiple stores (mixed combinations)"
)
@limiter.limit("20/minute")
async def browse_outfits_mixed(request: Request, prompt_request: OutfitPromptRequest):
    """
    Browse outfit combinations from ALL stores (ASOS + Amazon)
    Creates mixed combinations: e.g., ASOS top + Amazon bottom
    
    - Requires Google sign-in
    - Limited to 1 search per user (lifetime)
    - Returns 3 outfit combinations per search
    """
    start_time = time.time()
    
    try:
        # Check authentication
        user_id = await get_firebase_user(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Please sign in with Google to browse outfits."
            )
        
        # Check usage limits (per-user AND global)
        usage = get_user_usage(user_id)
        if not usage["can_search"]:
            if usage["search_exhausted"]:
                raise HTTPException(
                    status_code=429,
                    detail="You've already used your 1 free search. Thank you for trying our app!"
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Sorry, we've reached our search limit. Please try again later."
                )
        
        # Increment usage (user + global)
        if not increment_search(user_id):
            raise HTTPException(status_code=429, detail="Unable to process. Please try again.")
        
        gender = prompt_request.gender or "women"
        logger.info(f"🔀 Mixed store browse for user {user_id[:8]}...: {prompt_request.prompt}")
        
        if not settings.RAPIDAPI_KEY:
            raise HTTPException(status_code=503, detail="API not configured")
        
        # Parse prompt with LLM
        parsed_prompt = await llm_service.parse_outfit_prompt(prompt_request.prompt)
        logger.info(f"✅ Parsed: {parsed_prompt.dict()}")
        
        # Fetch from BOTH stores in parallel
        import asyncio
        asos_task = asos_service.browse_fashion(
            prompt=prompt_request.prompt,
            num_tops=3,
            num_bottoms=3,
            gender=gender
        )
        amazon_task = amazon_service.browse_fashion(
            prompt=prompt_request.prompt,
            num_tops=3,
            num_bottoms=3,
            gender=gender
        )
        
        asos_result, amazon_result = await asyncio.gather(asos_task, amazon_task)
        
        # Combine products from both stores
        all_tops = []
        all_bottoms = []
        
        # Add ASOS products
        for t in asos_result.get("tops", []):
            t["source"] = "asos"
            all_tops.append(t)
        for b in asos_result.get("bottoms", []):
            b["source"] = "asos"
            all_bottoms.append(b)
        
        # Add Amazon products
        for t in amazon_result.get("tops", []):
            t["source"] = "amazon"
            all_tops.append(t)
        for b in amazon_result.get("bottoms", []):
            b["source"] = "amazon"
            all_bottoms.append(b)
        
        logger.info(f"📦 Combined: {len(all_tops)} tops, {len(all_bottoms)} bottoms from both stores")
        
        if not all_tops or not all_bottoms:
            raise HTTPException(status_code=404, detail="No matching products found")
        
        # Create product items with source info in brand
        top_items = [
            ProductItem(
                id=t["id"], name=t["name"], category="top",
                price=t["price"], currency=t.get("currency", "INR"),
                image_url=t["image_url"], buy_url=t["buy_url"],
                brand=f"{t.get('brand', 'Unknown')} ({t.get('source', 'unknown').upper()})",
                description=t.get("description", ""),
            )
            for t in all_tops
        ]
        
        bottom_items = [
            ProductItem(
                id=b["id"], name=b["name"], category="bottom",
                price=b["price"], currency=b.get("currency", "INR"),
                image_url=b["image_url"], buy_url=b["buy_url"],
                brand=f"{b.get('brand', 'Unknown')} ({b.get('source', 'unknown').upper()})",
                description=b.get("description", ""),
            )
            for b in all_bottoms
        ]
        
        # Create MIXED combinations (max 3) - prioritize cross-store combos
        outfit_combinations = product_service.create_mixed_outfit_combinations(
            tops=top_items,
            bottoms=bottom_items,
            max_combinations=3
        )
        
        # Build response
        generated_outfits = [
            GeneratedOutfit(
                outfit_id=f"mix_{uuid.uuid4().hex[:8]}",
                prompt=prompt_request.prompt,
                combination=combo,
                tryon_image_url=None,
                created_at=datetime.now()
            )
            for combo in outfit_combinations
        ]
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Found {len(generated_outfits)} mixed outfits in {processing_time:.2f}s")
        
        return OutfitResponse(
            success=True,
            message=f"Found {len(generated_outfits)} mixed outfits from ASOS + Amazon",
            outfits=generated_outfits,
            total_count=len(generated_outfits),
            processing_time=processing_time,
            parsed_prompt=parsed_prompt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Mixed Store Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VIRTUAL TRY-ON ====================

class TryOnRequest(BaseModel):
    top_image_url: Optional[str] = None
    bottom_image_url: Optional[str] = None
    model_image_url: Optional[str] = None
    top_image_base64: Optional[str] = None
    bottom_image_base64: Optional[str] = None

class TryOnResponse(BaseModel):
    success: bool
    tryon_image_url: str
    processing_time: float

@app.post(
    f"{settings.API_PREFIX}/outfits/tryon",
    response_model=TryOnResponse,
    tags=["Outfits"],
    summary="Generate virtual try-on"
)
@limiter.limit("5/minute")
async def generate_tryon(request: Request, tryon_request: TryOnRequest):
    """
    Generate virtual try-on for an outfit
    
    - Requires Google sign-in
    - Limited to 1 try-on per 5 days
    """
    start_time = time.time()
    
    try:
        # Check authentication
        user_id = await get_firebase_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Please sign in to use try-on")
        
        # Check usage limits (per-user AND global)
        usage = get_user_usage(user_id)
        if not usage["can_tryon"]:
            if usage["tryon_exhausted"]:
                raise HTTPException(
                    status_code=429,
                    detail="You've already used your 1 free virtual try-on. Thank you for trying our app!"
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Sorry, we've reached our try-on limit. Please try again later."
                )
        
        # Increment usage (user + global)
        if not increment_tryon(user_id):
            raise HTTPException(status_code=429, detail="Unable to process. Please try again.")
        
        # Get model image
        model_url = tryon_request.model_image_url or settings.MODEL_IMAGE_URL
        
        # Process images (base64 preferred, fallback to URL)
        top_image_url = None
        bottom_image_url = None
        
        if tryon_request.top_image_base64:
            top_pil = tryon_service.base64_to_image(tryon_request.top_image_base64)
            top_image_url = await tryon_service._upload_to_cloudinary(top_pil, "tryon_top")
        elif tryon_request.top_image_url:
            top_image_url = tryon_request.top_image_url
        else:
            raise HTTPException(status_code=400, detail="No top image provided")
        
        if tryon_request.bottom_image_base64:
            bottom_pil = tryon_service.base64_to_image(tryon_request.bottom_image_base64)
            bottom_image_url = await tryon_service._upload_to_cloudinary(bottom_pil, "tryon_bottom")
        elif tryon_request.bottom_image_url:
            bottom_image_url = tryon_request.bottom_image_url
        else:
            raise HTTPException(status_code=400, detail="No bottom image provided")
        
        logger.info(f"🎨 Generating try-on for user {user_id[:8]}...")
        
        # Generate try-on
        result_image = await tryon_service.generate_full_outfit_tryon(
            model_image_url=model_url,
            top_image_url=top_image_url,
            bottom_image_url=bottom_image_url
        )
        
        # Fallback if AI fails
        if not result_image:
            logger.warning("⚠️ AI try-on failed, using fallback...")
            from app.services.garment_extractor import garment_extractor
            top_img = await garment_extractor.download_image(top_image_url)
            bottom_img = await garment_extractor.download_image(bottom_image_url)
            
            if top_img and bottom_img:
                if top_img.mode == 'RGBA':
                    top_img = top_img.convert('RGB')
                if bottom_img.mode == 'RGBA':
                    bottom_img = bottom_img.convert('RGB')
                result_image = tryon_service.create_outfit_preview(top_img, bottom_img)
            else:
                raise HTTPException(status_code=503, detail="Unable to process images")
        
        tryon_url = tryon_service.image_to_data_url(result_image)
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Try-on generated in {processing_time:.2f}s")
        
        return TryOnResponse(
            success=True,
            tryon_image_url=tryon_url,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== UPLOAD IMAGE ====================

class UploadResponse(BaseModel):
    success: bool
    image_url: str
    filename: str

@app.post(
    f"{settings.API_PREFIX}/upload/model-image",
    response_model=UploadResponse,
    tags=["Upload"],
    summary="Upload user photo for try-on"
)
async def upload_model_image(file: UploadFile = File(...)):
    """Upload a user photo for virtual try-on"""
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        content = await file.read()
        public_id = f"user_models/user_{uuid.uuid4().hex[:12]}"
        
        result = cloudinary.uploader.upload(
            io.BytesIO(content),
            public_id=public_id,
            resource_type="image",
            overwrite=True
        )
        
        image_url = result.get('secure_url')
        logger.info(f"✅ Uploaded: {image_url}")
        
        return UploadResponse(success=True, image_url=image_url, filename=public_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USAGE ====================

@app.get(f"{settings.API_PREFIX}/usage", tags=["Usage"])
async def get_usage(request: Request):
    """Get current user's usage stats"""
    user_id = await get_firebase_user(request)
    global_usage = get_global_usage()
    
    if not user_id:
        return {
            "search_count": 0,
            "tryon_count": 0,
            "search_limit": 1,
            "tryon_limit": 1,
            "can_search": global_usage["searches_available"],
            "can_tryon": global_usage["tryons_available"],
            "authenticated": False,
            "global_searches_remaining": global_usage["searches_remaining"],
            "global_tryons_remaining": global_usage["tryons_remaining"],
        }
    
    usage = get_user_usage(user_id)
    usage["authenticated"] = True
    return usage


@app.get(f"{settings.API_PREFIX}/admin/stats", tags=["Admin"])
async def admin_stats():
    """
    Get admin statistics (for monitoring usage)
    Shows total users, searches used, try-ons used, remaining limits
    """
    return get_admin_stats()


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "error_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )


# ==================== ROOT ====================

@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
