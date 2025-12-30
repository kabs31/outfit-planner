"""
Debug script to test image downloading and processing logic
"""
import asyncio
import httpx
from PIL import Image
import io
import traceback
from app.config import settings

async def download_image(url: str):
    print(f"Downloading {url}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error content: {response.text[:200]}")
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            return image
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

async def test_process():
    # Test URLs from our custom_products.json
    top_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"
    bottom_url = "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500"
    model_url = settings.MODEL_IMAGE_URL
    
    # 1. Download Top
    top_img = await download_image(top_url)
    if not top_img: return
    print("✅ Top image downloaded")
    
    # 2. Download Bottom
    bottom_img = await download_image(bottom_url)
    if not bottom_img: return
    print("✅ Bottom image downloaded")
    
    # 3. Download Model
    print(f"Downloading model image: {model_url}")
    model_img = await download_image(model_url)
    if not model_img: return
    print("✅ Model image downloaded")
    
    # 4. Test combination (logic from tryon_service)
    try:
        height = 768
        top_ratio = height / top_img.height
        bottom_ratio = height / bottom_img.height
        
        top_resized = top_img.resize(
            (int(top_img.width * top_ratio), height),
            Image.Resampling.LANCZOS
        )
        print("✅ Top resized")
        
        bottom_resized = bottom_img.resize(
            (int(bottom_img.width * bottom_ratio), height),
            Image.Resampling.LANCZOS
        )
        print("✅ Bottom resized")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_process())
