"""
Garment Extractor Service
Extracts clothing items from product images using:
1. Replicate's clothing-segmentation model with MASK approach (best quality)
2. rembg as fallback
"""
import io
import os
import logging
import httpx
from PIL import Image
from rembg import remove, new_session
from typing import Optional, Tuple
import base64
import asyncio
import uuid

import cloudinary
import cloudinary.uploader

from app.config import settings

logger = logging.getLogger(__name__)

# Replicate model for clothing segmentation
CLOTHING_SEG_MODEL = "naklecha/clothing-segmentation:501aa8488496fffc6bbee9544729dc28654649f2e3c80de0bf08fb9fe71898f8"

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


class GarmentExtractor:
    """Service to extract garments from product images using mask-based extraction"""
    
    def __init__(self):
        # Initialize rembg session as fallback
        logger.info("Initializing garment extractor with mask-based extraction...")
        try:
            self.rembg_session = new_session("u2net_cloth_seg")
            logger.info("rembg fallback ready with u2net_cloth_seg")
        except Exception as e:
            logger.warning(f"Could not load cloth_seg model, falling back to default: {e}")
            self.rembg_session = new_session("u2net")
        
        # Check Replicate token
        self.replicate_token = getattr(settings, 'REPLICATE_API_TOKEN', '')
        if self.replicate_token:
            os.environ['REPLICATE_API_TOKEN'] = self.replicate_token
            logger.info("Replicate clothing segmentation enabled (mask approach)")
        else:
            logger.warning("No Replicate token - will use rembg only")
    
    async def download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL with proper headers, with multiple fallback strategies"""
        
        # Strategy 1: Direct download with full browser-like headers
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
            
            # Add referer based on URL
            if "asos" in url.lower():
                headers["Referer"] = "https://www.asos.com/"
                headers["Origin"] = "https://www.asos.com"
            
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200 and len(response.content) > 1000:
                    logger.info(f"Direct download successful ({len(response.content)} bytes)")
                    return Image.open(io.BytesIO(response.content)).convert("RGBA")
                elif response.status_code in [403, 401]:
                    logger.info(f"Direct download blocked ({response.status_code})")
                else:
                    logger.warning(f"Download returned status {response.status_code}")
        except httpx.TimeoutException:
            logger.warning("Direct download timed out")
        except Exception as e:
            logger.warning(f"Direct download failed: {e}")
        
        # Strategy 2: Try with requests library (different HTTP client)
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/*",
                "Referer": "https://www.google.com/",
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code == 200 and len(response.content) > 1000:
                logger.info(f"Requests library download successful ({len(response.content)} bytes)")
                return Image.open(io.BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            logger.warning(f"Requests library download failed: {e}")
        
        # Strategy 3: Use Cloudinary's fetch feature (proxies the image)
        logger.info("Trying Cloudinary fetch...")
        return await self._download_via_cloudinary(url)
    
    async def _download_via_cloudinary(self, url: str) -> Optional[Image.Image]:
        """Use Cloudinary's fetch feature to download blocked images"""
        try:
            import urllib.parse
            # Cloudinary fetch URL - this acts as a proxy
            encoded_url = urllib.parse.quote(url, safe='')
            cloudinary_url = f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/image/fetch/{encoded_url}"
            
            logger.info(f"Fetching via Cloudinary: {cloudinary_url[:80]}...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(cloudinary_url, follow_redirects=True)
                if response.status_code == 200:
                    logger.info("Cloudinary fetch successful!")
                    return Image.open(io.BytesIO(response.content)).convert("RGBA")
                else:
                    logger.error(f"Cloudinary fetch failed: {response.status_code}")
                    # Try uploading the URL directly to Cloudinary as a remote fetch
                    return await self._upload_and_download(url)
        except Exception as e:
            logger.error(f"Cloudinary fetch error: {e}")
            return await self._upload_and_download(url)
    
    async def _upload_and_download(self, url: str) -> Optional[Image.Image]:
        """Upload remote URL to Cloudinary and download the result"""
        try:
            logger.info("Trying Cloudinary remote upload...")
            # Use Cloudinary's ability to upload from URL directly
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                url,
                resource_type="image"
                # Don't use type="fetch" - just upload the URL directly
            )
            if result and result.get('secure_url'):
                # Download from our Cloudinary
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(result['secure_url'])
                    if response.status_code == 200:
                        logger.info("Cloudinary upload+download successful!")
                        return Image.open(io.BytesIO(response.content)).convert("RGBA")
            return None
        except Exception as e:
            logger.error(f"Cloudinary upload+download failed: {e}")
            return None
    
    async def upload_to_cloudinary(self, image: Image.Image, prefix: str = "garment") -> Optional[str]:
        """Upload PIL Image to Cloudinary and return URL"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            public_id = f"garments/{prefix}_{uuid.uuid4().hex[:8]}"
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                buffer,
                public_id=public_id,
                resource_type="image"
            )
            return result.get('secure_url')
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            return None
    
    def _run_replicate_segmentation_with_mask(
        self, 
        image_url: str, 
        clothing_type: str
    ) -> Tuple[Optional[bytes], Optional[bytes]]:
        """
        Run Replicate clothing segmentation and return mask bytes
        
        Returns:
            Tuple of (mask_bytes, original_bytes) or (None, None)
        """
        try:
            import replicate
            
            output = replicate.run(
                CLOTHING_SEG_MODEL,
                input={
                    "image": image_url,
                    "clothing": clothing_type
                }
            )
            
            # Output is a list of 3 FileOutput objects:
            # [0] = original image
            # [1] = segmentation mask <- USE THIS AS MASK
            # [2] = masked image (pink overlay - not what we want)
            if output and len(output) >= 2:
                mask_bytes = output[1].read()
                return mask_bytes, None
            
            return None, None
            
        except Exception as e:
            logger.error(f"Replicate segmentation error: {e}")
            return None, None
    
    async def extract_garment_with_mask(
        self, 
        image_url: str, 
        original_image: Image.Image,
        clothing_type: str = "topwear"
    ) -> Optional[Image.Image]:
        """
        Extract garment using Replicate mask applied to original image
        
        This is the CORRECT approach:
        1. Get segmentation mask from Replicate
        2. Apply mask to original image to extract only clothing pixels
        
        Args:
            image_url: URL of the image (for Replicate API)
            original_image: PIL Image of the original (to apply mask to)
            clothing_type: "topwear" or "bottomwear"
            
        Returns:
            PIL Image with extracted garment (transparent background)
        """
        if not self.replicate_token:
            logger.warning("No Replicate token for mask extraction")
            return None
        
        try:
            logger.info(f"Extracting {clothing_type} using MASK approach...")
            
            # Run Replicate to get mask
            loop = asyncio.get_event_loop()
            mask_bytes, _ = await loop.run_in_executor(
                None,
                self._run_replicate_segmentation_with_mask,
                image_url,
                clothing_type
            )
            
            if not mask_bytes:
                logger.warning("No mask received from Replicate")
                return None
            
            # Load mask
            mask = Image.open(io.BytesIO(mask_bytes)).convert('L')
            
            # Resize mask to match original if needed
            if mask.size != original_image.size:
                mask = mask.resize(original_image.size, Image.Resampling.LANCZOS)
            
            # Apply mask to original image - extract only clothing pixels
            original_rgba = original_image.convert('RGBA')
            result = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
            result.paste(original_rgba, mask=mask)
            
            logger.info(f"Mask extraction successful! Size: {result.size}")
            return result
            
        except Exception as e:
            logger.error(f"Mask extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def extract_garment_rembg(self, image: Image.Image) -> Image.Image:
        """Extract garment using rembg (fallback method)"""
        try:
            result = remove(image, session=self.rembg_session)
            return result
        except Exception as e:
            logger.error(f"Error extracting garment with rembg: {e}")
            return image
    
    def add_white_background(self, image: Image.Image) -> Image.Image:
        """Add white background to transparent image"""
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            # Handle alpha channel
            if len(image.split()) == 4:
                background.paste(image, mask=image.split()[3])
            else:
                background.paste(image)
            return background
        return image.convert("RGB")
    
    async def extract_from_url(
        self, 
        url: str, 
        clothing_type: str = "topwear",
        add_white_bg: bool = True,
        use_replicate: bool = True
    ) -> Optional[Image.Image]:
        """
        Download image and extract garment using mask approach
        
        Args:
            url: URL of the product image
            clothing_type: "topwear" or "bottomwear"
            add_white_bg: Whether to add white background
            use_replicate: Whether to try Replicate first
            
        Returns:
            PIL Image with extracted garment
        """
        logger.info(f"Extracting {clothing_type} from: {url[:60]}...")
        
        # Download original image first
        original_image = await self.download_image(url)
        if not original_image:
            logger.error("Failed to download original image")
            return None
        
        extracted = None
        
        # Try Replicate MASK approach first (best quality)
        if use_replicate and self.replicate_token:
            # Upload to Cloudinary so Replicate can access it
            cloudinary_url = await self.upload_to_cloudinary(original_image, f"original_{clothing_type}")
            if cloudinary_url:
                extracted = await self.extract_garment_with_mask(
                    cloudinary_url, 
                    original_image, 
                    clothing_type
                )
        
        # Fallback to rembg if Replicate failed
        if not extracted:
            logger.info("Using rembg fallback...")
            extracted = self.extract_garment_rembg(original_image)
        
        if not extracted:
            logger.error("All extraction methods failed")
            return None
        
        # Add white background if requested
        if add_white_bg:
            extracted = self.add_white_background(extracted)
        
        logger.info("Garment extracted successfully!")
        return extracted
    
    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode()
    
    async def extract_and_upload(
        self, 
        url: str, 
        clothing_type: str = "topwear"
    ) -> Optional[str]:
        """Extract garment and upload to Cloudinary, return URL"""
        image = await self.extract_from_url(url, clothing_type=clothing_type, add_white_bg=True)
        if image:
            return await self.upload_to_cloudinary(image, f"extracted_{clothing_type}")
        return None


# Global instance
garment_extractor = GarmentExtractor()
