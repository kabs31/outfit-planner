"""
Test Local IDM-VTON Setup
Quick test to verify local GPU virtual try-on is working
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_local_vton():
    print("=" * 70)
    print("TESTING LOCAL IDM-VTON SETUP")
    print("=" * 70)
    
    # Check imports
    print("\n1️⃣  Checking imports...")
    try:
        import torch
        from app.services.local_vton_service import get_local_vton
        from app.config import settings
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\n💡 Run: pip install diffusers transformers accelerate safetensors")
        return False
    
    # Check GPU
    print("\n2️⃣  Checking GPU availability...")
    if not torch.cuda.is_available():
        print("❌ CUDA not available!")
        print("   Make sure you have NVIDIA GPU with drivers installed")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"✅ GPU: {gpu_name}")
    print(f"✅ VRAM: {vram_gb:.1f} GB")
    
    # Check configuration
    print("\n3️⃣  Checking configuration...")
    print(f"   USE_LOCAL_VTON: {settings.USE_LOCAL_VTON}")
    print(f"   VTON_STEPS: {settings.LOCAL_VTON_STEPS}")
    print(f"   VTON_RESOLUTION: {settings.LOCAL_VTON_WIDTH}x{settings.LOCAL_VTON_HEIGHT}")
    
    if not settings.USE_LOCAL_VTON:
        print("\n⚠️  USE_LOCAL_VTON is False!")
        print("   Set USE_LOCAL_VTON=true in backend/.env")
        return False
    
    # Initialize service
    print("\n4️⃣  Initializing local VTON service...")
    print("   (This will download ~10GB model on first run)")
    print("   Please wait...")
    
    try:
        service = get_local_vton()
        
        if not service or not service.is_loaded:
            print("❌ Service failed to initialize!")
            return False
        
        print("✅ Service initialized successfully!")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test generation
    print("\n5️⃣  Testing image generation...")
    print("   Downloading test images...")
    
    try:
        from PIL import Image
        import requests
        import io
        
        model_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"
        garment_url = "https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=500"
        
        model_img = Image.open(io.BytesIO(requests.get(model_url).content))
        garment_img = Image.open(io.BytesIO(requests.get(garment_url).content))
        
        print("✅ Test images downloaded")
        
        print("\n   Generating try-on image...")
        print("   ⏱️  Expected time: 25-40 seconds on RTX 4060")
        print("   (First generation may take longer)")
        
        import time
        start = time.time()
        
        result = service.generate(
            model_image=model_img,
            garment_image=garment_img,
            num_steps=15,  # Lower steps for faster test
            width=384,  # Lower resolution for faster test
            height=576
        )
        
        elapsed = time.time() - start
        
        if result:
            output_path = "test_local_vton_result.png"
            result.save(output_path)
            print(f"\n✅ SUCCESS! Generated in {elapsed:.1f}s")
            print(f"✅ Saved to: {Path(output_path).absolute()}")
            
            # Cleanup
            service.unload_model()
            print("\n✅ Model unloaded from GPU")
            
            return True
        else:
            print("\n❌ Generation failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_local_vton()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nYour local IDM-VTON is ready!")
        print("\nNext steps:")
        print("  1. Restart your backend server")
        print("  2. Open http://localhost:5173")
        print("  3. Generate outfits and see AI try-on images!")
    else:
        print("❌ TESTS FAILED")
        print("\nPlease fix the errors above and try again.")
        print("\nCommon fixes:")
        print("  1. Set USE_LOCAL_VTON=true in backend/.env")
        print("  2. Install dependencies: pip install diffusers transformers accelerate")
        print("  3. Make sure GPU drivers are installed")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
