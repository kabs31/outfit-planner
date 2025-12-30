"""
Test RunPod Integration
Verifies connectivity to IDM-VTON endpoint
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_runpod():
    print("=" * 60)
    print("TESTING RUNPOD CONNECTION")
    print("=" * 60)
    
    try:
        from app.config import settings
        from app.services.tryon_service import VirtualTryOnService
        
        print(f"✅ API Key: {settings.RUNPOD_API_KEY[:4]}...{settings.RUNPOD_API_KEY[-4:]}")
        print(f"✅ Endpoint: {settings.RUNPOD_ENDPOINT_ID}")
        
        service = VirtualTryOnService()
        
        print("\n1️⃣  Sending test generation request...")
        print("   (This might take 60-90s if cold start)")
        
        # Use dummy images for connection test
        # We just want to see if the API responds, not waste credits on full gen if possible
        # But tryon service requires images... let's try a real generation
        
        from PIL import Image
        import requests
        import io
        
        print("   Downloading test images...")
        model_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"
        garment_url = "https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=500"
        
        model_img = Image.open(io.BytesIO(requests.get(model_url).content))
        garment_img = Image.open(io.BytesIO(requests.get(garment_url).content))
        
        # Combine (simulating what app does)
        # combined = service.combine_product_images(garment_img, garment_img) 
        
        print("🚀 Sending request to RunPod...")
        result = await service.generate_tryon_image_runpod(
            model_image_url=model_url,
            garment_image=garment_img,
            category="upper_body"
        )
        
        if result:
            print("\n✅ SUCCESS! Image generated!")
            print(f"   Base64 length: {len(result)}")
            return True
        else:
            print("\n❌ Generation failed. Check logs.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_runpod())
