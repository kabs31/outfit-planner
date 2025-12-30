"""
Test script to check if outfit finding works (without image generation)
"""
import sys
import os
os.environ['DATABASE_URL'] = 'sqlite:///./backend/outfit_planner.db'

sys.path.append('backend')

from app.services.product_service import ProductService
from app.database import SessionLocal

# Initialize service
product_service = ProductService()
db = SessionLocal()

# Test prompt
prompt = "beach party, colorful and relaxed"

print(f"Testing outfit generation for: '{prompt}'\n")
print("="*80)

try:
    # Call the actual outfit finding function
    outfits = product_service.find_matching_outfits(db, prompt, num_outfits=3)
    
    print(f"\n✅ Found {len(outfits)} outfit combinations!\n")
    
    for i, outfit in enumerate(outfits, 1):
        print(f"\n--- Outfit {i} ---")
        print(f"TOP: {outfit.top.name}")
        print(f"  Category: {outfit.top.category}")
        print(f"  Price: {outfit.top.currency} {outfit.top.price}")
        print(f"  Image: {outfit.top.image_url}")
        
        print(f"\nBOTTOM: {outfit.bottom.name}")
        print(f"  Category: {outfit.bottom.category}")
        print(f"  Price: {outfit.bottom.currency} {outfit.bottom.price}")
        print(f"  Image: {outfit.bottom.image_url}")
        
        print(f"\nTotal outfit price: ₹{outfit.total_price}")
        print(f"Style match: {outfit.style_match}")
        print("-"*80)
        
finally:
    db.close()
