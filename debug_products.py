"""
Debug script to check what products are in the database
"""
import sys
sys.path.append('backend')

from app.database import SessionLocal, Product

db = SessionLocal()
try:
    products = db.query(Product).all()
    print(f"Total products: {len(products)}")
    print("\n" + "="*80)
    
    for p in products:
        print(f"\nID: {p.id}")
        print(f"Name: {p.name}")
        print(f"Category: {p.category}")
        print(f"Price: {p.price}")
        print(f"Brand: {p.brand}")
        print(f"Description: {p.description[:100] if p.description else 'None'}...")
        print(f"Is Active: {p.is_active}")
        print(f"Has Embedding: {p.embedding is not None}")
        print("-" * 80)
        
finally:
    db.close()
