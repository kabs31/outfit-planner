"""
Virtual Try-On Service - IDM-VTON Integration
Generates photo-realistic images of models wearing outfits using RunPod GPU
"""
import httpx
import base64
import io
import cloudinary
import cloudinary.uploader
from PIL import Image
from typing import Optional, Tuple
import logging
import time
import asyncio

from app.config import settings
from app.models import OutfitCombination

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


class VirtualTryOnService:
    """Service for generating virtual try-on images using IDM-VTON"""
    
    def __init__(self):
        self.runpod_api_key = settings.RUNPOD_API_KEY
        self.endpoint_id = settings.RUNPOD_ENDPOINT_ID
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
    
    # ==================== IMAGE PROCESSING ====================
    
    async def download_image(self, url: str) -> Image.Image:
        """Download image from URL"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
                return image
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize image to specified size"""
        return image.resize(size, Image.Resampling.LANCZOS)
    
    def combine_product_images(
        self, 
        top_image: Image.Image, 
        bottom_image: Image.Image
    ) -> Image.Image:
        """
        Combine top and bottom product images side by side
        This creates a reference image for virtual try-on
        """
        # Resize both to same height
        height = 768
        top_ratio = height / top_image.height
        bottom_ratio = height / bottom_image.height
        
        top_resized = top_image.resize(
            (int(top_image.width * top_ratio), height),
            Image.Resampling.LANCZOS
        )
        bottom_resized = bottom_image.resize(
            (int(bottom_image.width * bottom_ratio), height),
            Image.Resampling.LANCZOS
        )
        
        # Create combined image
        total_width = top_resized.width + bottom_resized.width
        combined = Image.new('RGB', (total_width, height), (255, 255, 255))
        combined.paste(top_resized, (0, 0))
        combined.paste(bottom_resized, (top_resized.width, 0))
        
        return combined
    
    # ==================== RUNPOD INTEGRATION ====================
    
    async def generate_tryon_image_runpod(
        self,
        model_image_url: str,
        garment_image: Image.Image,
        category: str = "upper_body"  # or "lower_body" or "dresses"
    ) -> Optional[str]:
        """
        Generate virtual try-on image using RunPod IDM-VTON endpoint
        
        Args:
            model_image_url: URL of model/person image
            garment_image: PIL Image of garment
            category: Type of garment
            
        Returns:
            Base64 encoded result image or None if failed
        """
        try:
            # Convert garment to base64
            garment_base64 = self.image_to_base64(garment_image)
            
            # Prepare request payload
            payload = {
                "input": {
                    "model_image": model_image_url,
                    "garment_image": garment_base64,
                    "category": category,
                    "num_inference_steps": settings.TRYON_STEPS,
                    "guidance_scale": settings.TRYON_GUIDANCE_SCALE,
                    "seed": -1  # Random seed
                }
            }
            
            # Make request to RunPod
            headers = {
                "Authorization": f"Bearer {self.runpod_api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Submit job
                logger.info("Submitting try-on job to RunPod...")
                response = await client.post(
                    f"{self.base_url}/run",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                job_data = response.json()
                job_id = job_data.get('id')
                
                if not job_id:
                    logger.error("No job ID returned from RunPod")
                    return None
                
                logger.info(f"Job submitted: {job_id}")
                
                # Poll for results
                max_attempts = 60  # 60 attempts = 2 minutes max
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)  # Wait 2 seconds between polls
                    
                    status_response = await client.get(
                        f"{self.base_url}/status/{job_id}",
                        headers=headers
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    status = status_data.get('status')
                    logger.info(f"Job status: {status} (attempt {attempt + 1}/{max_attempts})")
                    
                    if status == 'COMPLETED':
                        output = status_data.get('output', {})
                        result_image = output.get('image')
                        
                        if result_image:
                            logger.info("✅ Try-on image generated successfully")
                            return result_image
                        else:
                            logger.error("No image in completed job output")
                            return None
                    
                    elif status in ['FAILED', 'CANCELLED']:
                        error = status_data.get('error', 'Unknown error')
                        logger.error(f"Job failed: {error}")
                        return None
                
                logger.error("Job timed out")
                return None
                
        except Exception as e:
            logger.error(f"❌ RunPod try-on generation failed: {e}")
            return None
    
    # ==================== LOCAL DEVELOPMENT FALLBACK ====================
    
    async def generate_tryon_image_local(
        self,
        model_image: Image.Image,
        garment_image: Image.Image
    ) -> Optional[Image.Image]:
        """
        LOCAL DEVELOPMENT: Simple image compositing for testing
        This is NOT real virtual try-on, just for development without GPU
        
        In production, this should never be used - use RunPod instead
        """
        try:
            logger.warning("⚠️  Using LOCAL fallback - not real virtual try-on!")
            
            # Simple side-by-side composition
            width = 512
            height = 768
            
            model_resized = self.resize_image(model_image, (width // 2, height))
            garment_resized = self.resize_image(garment_image, (width // 2, height))
            
            result = Image.new('RGB', (width, height))
            result.paste(model_resized, (0, 0))
            result.paste(garment_resized, (width // 2, 0))
            
            return result
            
        except Exception as e:
            logger.error(f"Local fallback failed: {e}")
            return None
    
    # ==================== MAIN GENERATION FUNCTION ====================
    
    async def generate_outfit_image(
        self,
        outfit: OutfitCombination,
        use_local: bool = False
    ) -> Optional[str]:
        """
        Generate complete outfit try-on image
        
        Args:
            outfit: Outfit combination
            use_local: If True, use local fallback (for development)
            
        Returns:
            Cloudinary URL of generated image or None if failed
        """
        start_time = time.time()
        
        try:
            logger.info("Starting outfit image generation...")
            
            # Download product images
            logger.info("Downloading product images...")
            top_image = await self.download_image(str(outfit.top.image_url))
            bottom_image = await self.download_image(str(outfit.bottom.image_url))
            
            # Combine product images
            combined_garment = self.combine_product_images(top_image, bottom_image)
            
            # Generate try-on image
            if use_local or not settings.RUNPOD_API_KEY:
                # Local development fallback
                logger.warning("Using local fallback (not real virtual try-on)")
                
                # Get model image
                model_image = await self.download_image(settings.MODEL_IMAGE_URL)
                result_image = await self.generate_tryon_image_local(
                    model_image, 
                    combined_garment
                )
                
                if not result_image:
                    return None
                
                # Convert to base64 for upload
                result_base64 = self.image_to_base64(result_image)
                upload_data = f"data:image/png;base64,{result_base64}"
                
            else:
                # Production: Use RunPod
                logger.info("Generating with RunPod IDM-VTON...")
                result_base64 = await self.generate_tryon_image_runpod(
                    model_image_url=settings.MODEL_IMAGE_URL,
                    garment_image=combined_garment,
                    category="upper_body"  # Can be made dynamic
                )
                
                if not result_base64:
                    return None
                
                upload_data = f"data:image/png;base64,{result_base64}"
            
            # Upload to Cloudinary
            logger.info("Uploading to Cloudinary...")
            upload_result = cloudinary.uploader.upload(
                upload_data,
                folder="outfits",
                use_filename=False,
                unique_filename=True
            )
            
            image_url = upload_result['secure_url']
            generation_time = time.time() - start_time
            
            logger.info(f"✅ Outfit image generated in {generation_time:.2f}s: {image_url}")
            return image_url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate outfit image: {e}")
            return None
    
    # ==================== BATCH GENERATION ====================
    
    async def generate_multiple_outfits(
        self,
        outfits: list[OutfitCombination],
        use_local: bool = False
    ) -> list[Optional[str]]:
        """
        Generate images for multiple outfits in parallel
        
        Args:
            outfits: List of outfit combinations
            use_local: Use local fallback
            
        Returns:
            List of Cloudinary URLs (None for failed generations)
        """
        tasks = [
            self.generate_outfit_image(outfit, use_local)
            for outfit in outfits
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
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


# ==================== TESTING ====================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = VirtualTryOnService()
        
        print("=" * 60)
        print("Testing Virtual Try-On Service")
        print("=" * 60)
        
        # Create mock outfit
        from app.models import ProductItem, OutfitCombination, ClothingCategory
        
        mock_top = ProductItem(
            id="test_top",
            name="Test Shirt",
            category=ClothingCategory.TOP,
            price=999,
            image_url="https://fakestoreapi.com/img/71-3HjGNDUL._AC_SY879._SX._UX._SY._UY_.jpg",
            buy_url="https://test.com"
        )
        
        mock_bottom = ProductItem(
            id="test_bottom",
            name="Test Pants",
            category=ClothingCategory.BOTTOM,
            price=1299,
            image_url="https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",
            buy_url="https://test.com"
        )
        
        mock_outfit = OutfitCombination(
            top=mock_top,
            bottom=mock_bottom,
            total_price=2298,
            match_score=0.85,
            style_tags=["casual"]
        )
        
        print("\nGenerating outfit image (local fallback)...")
        print("Note: This uses simple compositing, not real virtual try-on")
        
        result_url = await service.generate_outfit_image(mock_outfit, use_local=True)
        
        if result_url:
            print(f"✅ Generated: {result_url}")
        else:
            print("❌ Generation failed")
    
    asyncio.run(test())
