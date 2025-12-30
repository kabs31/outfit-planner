"""
Quick test to debug product sync
"""
import asyncio
import sys
sys.path.append('backend')

from app.database import SessionLocal, Product
from app.services.product_service import product_service

async def test_sync():
    db = SessionLocal()
    try:
        print("Fetching products from FakeStoreAPI...")
        api_products = await product_service.fetch_products_from_api()
        print(f"✅ Fetched {len(api_products)} products")
        
        if len(api_products) > 0:
            print("\nSample product:")
            print(api_products[0])
            
            print("\nSyncing to database...")
            count = await product_service.sync_products_to_db(db)
            print(f"✅ Synced {count} products")
            
            # Check database
            db_count = db.query(Product).count()
            print(f"📊 Total products in DB: {db_count}")
        else:
            print("❌ No products fetched from API")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync())
