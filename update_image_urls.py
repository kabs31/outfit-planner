"""
Update bottom products with valid image URLs from FakeStoreAPI
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Use SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./backend/outfit_planner.db'
sys.path.append('backend')
from app.database import Product

engine = create_engine('sqlite:///./backend/outfit_planner.db')
SessionLocal = sessionmaker(bind=engine)

# Use known working FakeStoreAPI images
image_updates = {
    "bottom_001": "https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",  # Mens jacket
    "bottom_002": "https://fakestoreapi.com/img/71li-ujtlUL._AC_UX679_.jpg",  # Mens jacket
    "bottom_003": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",  # Mens clothing
    "bottom_004": "https://fakestoreapi.com/img/71-3HjGNDUL._AC_SY879._SX._UX._SY._UY_.jpg",  # Mens clothing
    "bottom_005": "https://fakestoreapi.com/img/51eg55uWmdL._AC_UX679_.jpg",  # Womens jacket
    "bottom_006": "https://fakestoreapi.com/img/61pHAEJ4NML._AC_UX679_.jpg",  # Mens clothing
    "bottom_007": "https://fakestoreapi.com/img/71YAIFU48IL._AC_UL640_QL65_ML3_.jpg"  # Mens clothing
}

db = SessionLocal()
try:
    updated = 0
    for product_id, new_url in image_updates.items():
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.image_url = new_url
            updated += 1
            print(f"✅ Updated {product_id}: {new_url}")
    
    db.commit()
    print(f"\n✅ Updated {updated} product image URLs")
    
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
