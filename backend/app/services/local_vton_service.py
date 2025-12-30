"""
Local IDM-VTON Service - Optimized for 8GB VRAM
Runs AI-powered virtual try-on on local GPU (RTX 4060)
"""
import torch
from diffusers import AutoPipelineForInpainting, DPMSolverMultistepScheduler
from PIL import Image
import logging
import gc
import io
import base64
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LocalVTONService:
    """Local IDM-VTON service optimized for 8GB VRAM"""
    
    def __init__(self):
        """Initialize with memory optimizations for RTX 4060"""
        self.pipe = None
        self.is_loaded = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Load IDM-VTON model with 8GB VRAM optimizations"""
        try:
            logger.info("🔧 Loading IDM-VTON model (optimized for 8GB VRAM)...")
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"VRAM Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            
            # Load model with FP16 (half precision) to save 50% VRAM
            self.pipe = AutoPipelineForInpainting.from_pretrained(
                "yisol/IDM-VTON",
                torch_dtype=torch.float16,  # Half precision
                use_safetensors=True,
                low_cpu_mem_usage=True  # Minimize CPU RAM during loading
            )
            
            # Use DPM solver for faster inference
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )
            
            # Memory optimizations for 8GB VRAM
            self.pipe.enable_attention_slicing(1)  # Reduce attention memory usage
            self.pipe.enable_vae_slicing()  # Reduce VAE memory usage
            
            # Optional: Enable CPU offloading if OOM occurs
            # Uncomment this line if you get "out of memory" errors
            # self.pipe.enable_sequential_cpu_offload()
            
            # Move to GPU
            self.pipe.to("cuda")
            
            # Enable memory-efficient attention if available (xformers)
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                logger.info("✅ xformers memory-efficient attention enabled")
            except Exception:
                logger.info("ℹ️  xformers not available (optional optimization)")
            
            self.is_loaded = True
            logger.info("✅ IDM-VTON model loaded successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to load IDM-VTON model: {e}")
            logger.error("Will fall back to simple composite mode")
            self.is_loaded = False
    
    def _prepare_image(self, image: Image.Image, width: int, height: int) -> Image.Image:
        """Resize and prepare image for model"""
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Resize maintaining aspect ratio
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        
        # Pad to exact size
        result = Image.new("RGB", (width, height), (255, 255, 255))
        offset = ((width - image.width) // 2, (height - image.height) // 2)
        result.paste(image, offset)
        
        return result
    
    def _cleanup_memory(self):
        """Aggressive memory cleanup"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        gc.collect()
    
    def generate(
        self,
        model_image: Image.Image,
        garment_image: Image.Image,
        num_steps: int = None,
        guidance_scale: float = None,
        width: int = None,
        height: int = None,
        seed: int = -1
    ) -> Optional[Image.Image]:
        """
        Generate virtual try-on image
        
        Args:
            model_image: Photo of person/model
            garment_image: Photo of clothing item
            num_steps: Inference steps (higher = better quality, slower)
            guidance_scale: How closely to follow prompt
            width: Output width
            height: Output height
            seed: Random seed (-1 for random)
        
        Returns:
            Generated try-on image or None if failed
        """
        if not self.is_loaded:
            logger.error("Model not loaded, cannot generate")
            return None
        
        # Use config defaults if not specified
        num_steps = num_steps or settings.LOCAL_VTON_STEPS
        guidance_scale = guidance_scale or settings.LOCAL_VTON_GUIDANCE
        width = width or settings.LOCAL_VTON_WIDTH
        height = height or settings.LOCAL_VTON_HEIGHT
        
        try:
            # Clear memory before generation
            self._cleanup_memory()
            
            logger.info(f"🎨 Generating try-on image...")
            logger.info(f"   Steps: {num_steps}, Guidance: {guidance_scale}")
            logger.info(f"   Resolution: {width}x{height}")
            
            # Prepare images
            model_prep = self._prepare_image(model_image, width, height)
            garment_prep = self._prepare_image(garment_image, width, height)
            
            # Set up generator
            if seed == -1:
                generator = None
            else:
                generator = torch.Generator("cuda").manual_seed(seed)
            
            # Generate
            with torch.inference_mode():  # Saves memory
                result = self.pipe(
                    prompt="a person wearing clothes, high quality, detailed",
                    negative_prompt="blurry, low quality, distorted, deformed",
                    image=model_prep,
                    garment_image=garment_prep,
                    num_inference_steps=num_steps,
                    guidance_scale=guidance_scale,
                    height=height,
                    width=width,
                    generator=generator
                ).images[0]
            
            # Clean up after generation
            self._cleanup_memory()
            
            logger.info("✅ Try-on image generated successfully!")
            return result
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                logger.error("❌ GPU OUT OF MEMORY!")
                logger.error("Try these fixes:")
                logger.error("  1. Lower resolution (width=384, height=576)")
                logger.error("  2. Reduce steps (num_steps=15)")
                logger.error("  3. Enable CPU offload (uncomment in _initialize_model)")
                logger.error("  4. Close other GPU applications")
            else:
                logger.error(f"❌ Generation failed: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return None
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def unload_model(self):
        """Unload model from GPU to free VRAM"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.is_loaded = False
            self._cleanup_memory()
            logger.info("Model unloaded from GPU")


# Global instance (lazy loaded)
_local_vton_instance: Optional[LocalVTONService] = None


def get_local_vton() -> Optional[LocalVTONService]:
    """Get or create local VTON service instance"""
    global _local_vton_instance
    
    if not settings.USE_LOCAL_VTON:
        return None
    
    if _local_vton_instance is None:
        try:
            _local_vton_instance = LocalVTONService()
        except Exception as e:
            logger.error(f"Failed to initialize local VTON: {e}")
            return None
    
    return _local_vton_instance


# ==================== TESTING ====================

if __name__ == "__main__":
    import asyncio
    import sys
    import requests
    
    async def test():
        print("=" * 60)
        print("Testing Local IDM-VTON Service")
        print("=" * 60)
        
        # Check GPU
        if not torch.cuda.is_available():
            print("❌ CUDA not available! Need NVIDIA GPU.")
            sys.exit(1)
        
        print(f"\n✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"✅ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        
        # Initialize service
        print("\nInitializing service...")
        service = LocalVTONService()
        
        if not service.is_loaded:
            print("❌ Model failed to load!")
            sys.exit(1)
        
        # Download test images
        print("\nDownloading test images...")
        model_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"
        garment_url = "https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=500"
        
        model_img = Image.open(io.BytesIO(requests.get(model_url).content))
        garment_img = Image.open(io.BytesIO(requests.get(garment_url).content))
        
        print("✅ Test images downloaded")
        
        # Generate
        print("\n🎨 Generating try-on image...")
        print("(This will take 25-40 seconds on RTX 4060...)")
        
        import time
        start = time.time()
        
        result = service.generate(
            model_image=model_img,
            garment_image=garment_img,
            num_steps=20,  # Lower for faster testing
            width=512,
            height=768
        )
        
        elapsed = time.time() - start
        
        if result:
            output_path = "test_local_vton_result.png"
            result.save(output_path)
            print(f"\n✅ SUCCESS! Generated in {elapsed:.1f}s")
            print(f"✅ Saved to: {output_path}")
            print(f"\n📊 Performance: {elapsed:.1f}s (expected: 25-40s)")
        else:
            print("\n❌ Generation failed!")
        
        # Cleanup
        service.unload_model()
        print("\n✅ Model unloaded from GPU")
    
    asyncio.run(test())
