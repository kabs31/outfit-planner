"""
Virtual Try-On Service - IDM-VTON via Replicate
Uses: cuuupid/idm-vton model (best-in-class virtual try-on)
Supports: Replicate SDK with fallback to simple preview
"""
import httpx
import base64
import io
import os
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFilter
from typing import Optional, Tuple
import logging
import time
import asyncio
import requests
import replicate

from app.config import settings
from app.models import OutfitCombination

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

# IDM-VTON model info - best-in-class virtual try-on
REPLICATE_MODEL = "cuuupid/idm-vton"
REPLICATE_MODEL_VERSION = "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"


class VirtualTryOnService:
    """
    Service for generating virtual try-on images using IDM-VTON
    
    Supports TWO-PASS approach:
    1. First pass: Put TOP on model
    2. Second pass: Put BOTTOM on result from first pass
    """
    
    def __init__(self):
        # Replicate config (primary)
        self.replicate_token = getattr(settings, 'REPLICATE_API_TOKEN', '')
        
        # Legacy RunPod support (disabled)
        self.runpod_api_key = None
        self.runpod_base_url = None
        
        # Set environment variable for replicate SDK
        if self.replicate_token:
            os.environ['REPLICATE_API_TOKEN'] = self.replicate_token
            logger.info("✅ Replicate API configured for IDM-VTON")
        else:
            logger.warning("⚠️  Replicate API not configured, will use fallback preview")
    
    # ==================== CLOUDINARY UPLOAD ====================
    
    async def _upload_to_cloudinary(self, image: Image.Image, prefix: str = "extracted") -> Optional[str]:
        """Upload a PIL Image to Cloudinary and return the URL"""
        try:
            import uuid
            
            # Convert to bytes
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Generate unique ID
            public_id = f"garments/{prefix}_{uuid.uuid4().hex[:8]}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                buffer,
                public_id=public_id,
                resource_type="image",
                overwrite=True
            )
            
            url = result.get('secure_url')
            logger.info(f"Uploaded to Cloudinary: {url[:60]}...")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload to Cloudinary: {e}")
            return None
    
    # ==================== IMAGE PROCESSING ====================
    
    async def download_image(self, url: str) -> Image.Image:
        """Download image from URL"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                return image
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        # Ensure RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def base64_to_image(self, base64_str: str) -> Image.Image:
        """Convert base64 string to PIL Image"""
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        img_data = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(img_data))
    
    def image_to_data_url(self, image: Image.Image) -> str:
        """Convert PIL Image to data URL"""
        base64_str = self.image_to_base64(image)
        return f"data:image/png;base64,{base64_str}"
    
    def resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize image to specified size"""
        return image.resize(size, Image.Resampling.LANCZOS)
    
    def prepare_garment_image(self, image: Image.Image, target_size: Tuple[int, int] = (384, 512)) -> Image.Image:
        """Prepare garment image for IDM-VTON"""
        # Resize while maintaining aspect ratio
        ratio = min(target_size[0] / image.width, target_size[1] / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Create white background and center the image
        result = Image.new('RGB', target_size, (255, 255, 255))
        x = (target_size[0] - resized.width) // 2
        y = (target_size[1] - resized.height) // 2
        result.paste(resized, (x, y))
        
        return result
    
    # ==================== REPLICATE API (IDM-VTON) ====================
    
    def _run_replicate_sync(
        self,
        person_image_url: str,
        garment_image_url: str,
        category: str,
        garment_description: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """Synchronous Replicate call with retry logic for rate limits"""
        import time as sync_time
        
        for attempt in range(max_retries):
            try:
                output = replicate.run(
                    REPLICATE_MODEL_VERSION,
                    input={
                        "crop": False,
                        "seed": 42,
                        "steps": 30,
                        "category": category,
                        "force_dc": False,
                        "garm_img": garment_image_url,
                        "human_img": person_image_url,
                        "mask_only": False,
                        "garment_des": garment_description
                    }
                )
                # Return the URL string
                return str(output) if output else None
            except Exception as e:
                error_str = str(e)
                # Handle rate limiting (429 errors)
                if "429" in error_str or "rate limit" in error_str.lower() or "throttled" in error_str.lower():
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                    sync_time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Replicate call failed: {e}")
                    return None
        
        logger.error(f"Replicate call failed after {max_retries} retries due to rate limiting")
        return None
    
    async def generate_tryon_replicate(
        self,
        person_image_url: str,
        garment_image_url: str,
        category: str = "upper_body",
        garment_description: str = "clothing item"
    ) -> tuple[Optional[Image.Image], Optional[str]]:
        """
        Generate virtual try-on using Replicate API with IDM-VTON
        Model: cuuupid/idm-vton (best-in-class virtual try-on)
        
        Args:
            person_image_url: URL of person/model image
            garment_image_url: URL of garment image
            category: "upper_body", "lower_body", or "dresses"
            garment_description: Description of the garment
            
        Returns:
            Tuple of (PIL Image result, result URL) or (None, None) if failed
        """
        if not self.replicate_token:
            logger.warning("Replicate API token not configured")
            return None, None
        
        try:
            logger.info(f"Generating try-on with IDM-VTON (category: {category})...")
            logger.info(f"  Human: {person_image_url[:80]}...")
            logger.info(f"  Garment: {garment_image_url[:80]}...")
            
            # Run synchronous replicate call in executor
            loop = asyncio.get_event_loop()
            result_url = await loop.run_in_executor(
                None,
                self._run_replicate_sync,
                person_image_url,
                garment_image_url,
                category,
                garment_description
            )
            
            if not result_url:
                logger.error("IDM-VTON returned no result")
                return None, None
            
            logger.info(f"✅ IDM-VTON result: {result_url[:60]}...")
            
            # Download result image
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(result_url)
                result_image = Image.open(io.BytesIO(response.content))
            
            logger.info("✅ IDM-VTON try-on successful!")
            return result_image, result_url
                
        except Exception as e:
            logger.error(f"IDM-VTON try-on failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None
    
    # ==================== TWO-PASS FULL OUTFIT ====================
    
    async def generate_full_outfit_tryon(
        self,
        model_image_url: str,
        top_image_url: str,
        bottom_image_url: str
    ) -> Optional[Image.Image]:
        """
        TWO-PASS APPROACH: Generate full outfit try-on using IDM-VTON
        
        Pass 1: Put TOP on model
        Pass 2: Put BOTTOM on result from Pass 1 (using Replicate URL directly)
        
        Args:
            model_image_url: URL of base model/person image
            top_image_url: URL of top garment image
            bottom_image_url: URL of bottom garment image
            
        Returns:
            Final image with both garments or None if failed
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting TWO-PASS outfit generation with IDM-VTON...")
            logger.info("=" * 60)
            
            # IMPORTANT: Always upload images to Cloudinary for Replicate access
            # E-commerce sites like ASOS block direct access (403 errors)
            extracted_top_url = None
            extracted_bottom_url = None
            
            from app.services.garment_extractor import garment_extractor
            
            # Try extraction first (improves results), but ALWAYS ensure Cloudinary upload
            try:
                logger.info("Extracting garments using Replicate clothing-segmentation...")
                
                # Extract top garment (using Replicate's clothing segmentation)
                top_extracted = await garment_extractor.extract_from_url(
                    top_image_url, 
                    clothing_type="topwear"  # Specify we want top clothing
                )
                if top_extracted:
                    # Upload to Cloudinary for Replicate access
                    top_cloudinary_url = await self._upload_to_cloudinary(top_extracted, "extracted_top")
                    if top_cloudinary_url:
                        extracted_top_url = top_cloudinary_url
                        logger.info(f"✅ Top garment extracted and uploaded")
                
                # Extract bottom garment (using Replicate's clothing segmentation)
                bottom_extracted = await garment_extractor.extract_from_url(
                    bottom_image_url,
                    clothing_type="bottomwear"  # Specify we want bottom clothing
                )
                if bottom_extracted:
                    bottom_cloudinary_url = await self._upload_to_cloudinary(bottom_extracted, "extracted_bottom")
                    if bottom_cloudinary_url:
                        extracted_bottom_url = bottom_cloudinary_url
                        logger.info(f"✅ Bottom garment extracted and uploaded")
                        
            except Exception as e:
                logger.warning(f"Garment extraction failed: {e}")
            
            # FALLBACK: If extraction failed, download and upload raw images to Cloudinary
            # This ensures Replicate can access them (ASOS/other sites block direct access)
            if not extracted_top_url:
                logger.info("Uploading TOP image to Cloudinary (no extraction)...")
                top_image = await garment_extractor.download_image(top_image_url)
                if top_image:
                    extracted_top_url = await self._upload_to_cloudinary(top_image, "raw_top")
                    if extracted_top_url:
                        logger.info(f"✅ Top image uploaded to Cloudinary")
                    else:
                        logger.error("Failed to upload top image to Cloudinary")
                        return None
                else:
                    logger.error("Failed to download top image")
                    return None
            
            if not extracted_bottom_url:
                logger.info("Uploading BOTTOM image to Cloudinary (no extraction)...")
                bottom_image = await garment_extractor.download_image(bottom_image_url)
                if bottom_image:
                    extracted_bottom_url = await self._upload_to_cloudinary(bottom_image, "raw_bottom")
                    if extracted_bottom_url:
                        logger.info(f"✅ Bottom image uploaded to Cloudinary")
                    else:
                        logger.error("Failed to upload bottom image to Cloudinary")
                        return None
                else:
                    logger.error("Failed to download bottom image")
                    return None
            
            # Small delay to respect rate limits (extraction used API calls)
            logger.info("Waiting 5s before IDM-VTON to respect rate limits...")
            await asyncio.sleep(5)
            
            # PASS 1: Put TOP on model
            logger.info("PASS 1: Applying top garment...")
            pass1_image, pass1_url = await self.generate_tryon_replicate(
                person_image_url=model_image_url,
                garment_image_url=extracted_top_url,
                category="upper_body",
                garment_description="top clothing"
            )
            
            if not pass1_image or not pass1_url:
                logger.warning("Pass 1 failed, returning None...")
                return None
            
            logger.info("✅ PASS 1 complete!")
            
            # Wait to respect rate limits before pass 2
            logger.info("Waiting 5s before Pass 2 to respect rate limits...")
            await asyncio.sleep(5)
            
            # PASS 2: Put BOTTOM on result from Pass 1
            # Use the Replicate URL directly (it's already public)
            logger.info("PASS 2: Applying bottom garment...")
            pass2_image, pass2_url = await self.generate_tryon_replicate(
                person_image_url=pass1_url,  # Use Replicate URL directly!
                garment_image_url=extracted_bottom_url,
                category="lower_body",
                garment_description="bottom clothing"
            )
            
            if not pass2_image:
                logger.warning("Pass 2 failed, returning Pass 1 result...")
                return pass1_image  # Return at least the top try-on
            
            logger.info("=" * 60)
            logger.info("✅ PASS 2 complete! Full outfit generated!")
            logger.info("=" * 60)
            return pass2_image
            
        except Exception as e:
            logger.error(f"Two-pass generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    # ==================== RUNPOD INTEGRATION ====================
    
    async def generate_tryon_image_runpod(
        self,
        model_image_url: str,
        garment_image: Image.Image,
        category: str = "upper_body"
    ) -> Optional[str]:
        """Generate virtual try-on using RunPod"""
        if not self.runpod_api_key:
            return None
            
        try:
            garment_base64 = self.image_to_base64(garment_image)
            
            payload = {
                "input": {
                    "model_image": model_image_url,
                    "garment_image": garment_base64,
                    "category": category,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "seed": -1
                }
            }
            
            headers = {
                "Authorization": f"Bearer {getattr(self, 'runpod_api_key', '')}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                logger.info("Submitting job to RunPod...")
                response = await client.post(
                    f"{self.runpod_base_url}/run",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                job_data = response.json()
                job_id = job_data.get('id')
                
                if not job_id:
                    return None
                
                # Poll for results
                max_attempts = 150
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)
                    
                    status_response = await client.get(
                        f"{self.runpod_base_url}/status/{job_id}",
                        headers=headers
                    )
                    status_data = status_response.json()
                    status = status_data.get('status')
                    
                    if status == 'COMPLETED':
                        output = status_data.get('output', {})
                        return output.get('image')
                    elif status in ['FAILED', 'CANCELLED']:
                        return None
                
                return None
                
        except Exception as e:
            logger.error(f"RunPod generation failed: {e}")
            return None
    
    # ==================== SIMPLE FALLBACK ====================
    
    def create_outfit_preview(
        self, 
        top_image: Image.Image, 
        bottom_image: Image.Image
    ) -> Image.Image:
        """
        Create a beautiful outfit preview card (fallback when no AI available)
        """
        # Dimensions
        width = 600
        height = 800
        padding = 40
        gap = 30
        
        usable_width = width - (padding * 2)
        usable_height = (height - (padding * 2) - gap) // 2
        
        def resize_to_fit(img, max_width, max_height):
            ratio = min(max_width / img.width, max_height / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            return img.resize(new_size, Image.Resampling.LANCZOS)
        
        top_resized = resize_to_fit(top_image, usable_width, usable_height)
        bottom_resized = resize_to_fit(bottom_image, usable_width, usable_height)
        
        # Create canvas with gradient
        combined = Image.new('RGB', (width, height), (26, 26, 46))
        draw = ImageDraw.Draw(combined)
        
        for y in range(height):
            r = int(26 + (y / height) * 10)
            g = int(26 + (y / height) * 10)
            b = int(46 + (y / height) * 20)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add product areas
        top_area = Image.new('RGBA', (usable_width + 20, usable_height + 20), (255, 255, 255, 8))
        combined.paste(top_area, (padding - 10, padding - 10), top_area)
        
        bottom_area = Image.new('RGBA', (usable_width + 20, usable_height + 20), (255, 255, 255, 8))
        combined.paste(bottom_area, (padding - 10, padding + usable_height + gap - 10), bottom_area)
        
        # Center and paste images with shadows
        top_x = padding + (usable_width - top_resized.width) // 2
        top_y = padding + (usable_height - top_resized.height) // 2
        
        shadow = Image.new('RGBA', (top_resized.width + 20, top_resized.height + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([10, 10, top_resized.width + 10, top_resized.height + 10], fill=(0, 0, 0, 60))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
        combined.paste(shadow, (top_x - 10, top_y - 5), shadow)
        combined.paste(top_resized, (top_x, top_y))
        
        bottom_x = padding + (usable_width - bottom_resized.width) // 2
        bottom_y = padding + usable_height + gap + (usable_height - bottom_resized.height) // 2
        
        shadow2 = Image.new('RGBA', (bottom_resized.width + 20, bottom_resized.height + 20), (0, 0, 0, 0))
        shadow2_draw = ImageDraw.Draw(shadow2)
        shadow2_draw.rectangle([10, 10, bottom_resized.width + 10, bottom_resized.height + 10], fill=(0, 0, 0, 60))
        shadow2 = shadow2.filter(ImageFilter.GaussianBlur(radius=10))
        combined.paste(shadow2, (bottom_x - 10, bottom_y - 5), shadow2)
        combined.paste(bottom_resized, (bottom_x, bottom_y))
        
        return combined
    
    # ==================== MAIN GENERATION FUNCTION ====================
    
    async def generate_outfit_image(
        self,
        outfit: OutfitCombination,
        use_local: bool = False
    ) -> Optional[str]:
        """
        Generate outfit try-on image with fallback chain:
        1. Replicate (TWO-PASS full outfit) 
        2. RunPod (single pass)
        3. Simple preview (no AI)
        """
        start_time = time.time()
        
        try:
            logger.info("Starting outfit image generation...")
            
            # Download product images
            top_image = await self.download_image(str(outfit.top.image_url))
            bottom_image = await self.download_image(str(outfit.bottom.image_url))
            
            result_image = None
            
            # Try Replicate TWO-PASS (best quality)
            if self.replicate_token and not use_local:
                logger.info("Attempting Replicate TWO-PASS generation...")
                
                result_image = await self.generate_full_outfit_tryon(
                    model_image_url=settings.MODEL_IMAGE_URL,
                    top_image_url=str(outfit.top.image_url),
                    bottom_image_url=str(outfit.bottom.image_url)
                )
                
                if result_image:
                    logger.info("Replicate TWO-PASS successful!")
            
            # Try RunPod (single garment)
            if result_image is None and self.runpod_api_key and not use_local:
                logger.info("🚀 Attempting RunPod generation...")
                
                # Combine images for single-pass
                combined_garment = self.create_outfit_preview(top_image, bottom_image)
                
                result_base64 = await self.generate_tryon_image_runpod(
                    model_image_url=settings.MODEL_IMAGE_URL,
                    garment_image=combined_garment,
                    category="upper_body"
                )
                
                if result_base64:
                    result_image = self.base64_to_image(result_base64)
                    logger.info("✅ RunPod generation successful!")
            
            # Fallback: Simple preview
            if result_image is None:
                logger.info("📦 Using simple preview fallback...")
                result_image = self.create_outfit_preview(top_image, bottom_image)
            
            # Convert to data URL
            result_data_url = self.image_to_data_url(result_image)
            
            generation_time = time.time() - start_time
            logger.info(f"✅ Outfit image generated in {generation_time:.2f}s")
            
            return result_data_url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate outfit image: {e}")
            return None
    
    # ==================== BATCH GENERATION ====================
    
    async def generate_multiple_outfits(
        self,
        outfits: list[OutfitCombination],
        use_local: bool = False
    ) -> list[Optional[str]]:
        """Generate images for multiple outfits"""
        # For AI try-on, process sequentially to avoid rate limits
        if self.replicate_token and not use_local:
            results = []
            for outfit in outfits:
                result = await self.generate_outfit_image(outfit, use_local)
                results.append(result)
            return results
        
        # For fallback, can process in parallel
        tasks = [
            self.generate_outfit_image(outfit, use_local)
            for outfit in outfits
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        urls = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Generation failed: {result}")
                urls.append(None)
            else:
                urls.append(result)
        
        success_count = sum(1 for url in urls if url is not None)
        logger.info(f"Generated {success_count}/{len(outfits)} outfit images")
        
        return urls


# Global instance
tryon_service = VirtualTryOnService()
