"""
Add mock bottom products to the SQLite database
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer
import sys
import os

# Set environment variable to use SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./backend/outfit_planner.db'

sys.path.append('backend')

from app.database import Product

# Create SQLite engine directly
engine = create_engine('sqlite:///./backend/outfit_planner.db')
SessionLocal = sessionmaker(bind=engine)

# Load embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Mock bottom products data
bottom_products = [
    {
        "id": "bottom_001",
        "name": "Levi's Men's 511 Slim Fit Jeans",
        "category": "bottom",
        "price": 1299.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",
        "buy_url": "https://example.com/products/bottom_001",
        "brand": "Levi's",
        "description": "Classic slim fit jeans made from premium denim. Perfect for casual outings and everyday wear. Available in multiple washes.",
        "colors": ["blue", "black", "grey"],
        "sizes": ["28", "30", "32", "34", "36"],
        "style_tags": ["casual", "denim", "everyday", "slim-fit"],
        "season": "all",
        "occasion": "casual"
    },
    {
        "id": "bottom_002",
        "name": "Nike Sportswear Club Fleece Joggers",
        "category": "bottom",
        "price": 899.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",
        "buy_url": "https://example.com/products/bottom_002",
        "brand": "Nike",
        "description": "Comfortable fleece joggers perfect for workouts and relaxed activities. Soft brushed fleece with elastic waistband.",
        "colors": ["grey", "black", "navy"],
        "sizes": ["S", "M", "L", "XL"],
        "style_tags": ["sport", "casual", "athletic", "comfortable"],
        "season": "all",
        "occasion": "gym"
    },
    {
        "id": "bottom_003",
        "name": "Dockers Men's Chino Pants",
        "category": "bottom",
        "price": 1599.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/71li-ujtlUL._AC_UX679_.jpg",
        "buy_url": "https://example.com/products/bottom_003",
        "brand": "Dockers",
        "description": "Classic fit chino pants for business casual and formal occasions. Wrinkle-resistant fabric with a tailored look.",
        "colors": ["khaki", "navy", "black", "grey"],
        "sizes": ["28", "30", "32", "34", "36", "38"],
        "style_tags": ["formal", "business", "smart-casual", "professional"],
        "season": "all",
        "occasion": "formal"
    },
    {
        "id": "bottom_004",
        "name": "Men's Beach Shorts Casual Summer",
        "category": "bottom",
        "price": 599.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/71YAIFU48IL._AC_UL640_QL65_ML3_.jpg",
        "buy_url": "https://example.com/products/bottom_004",
        "brand": "Generic",
        "description": "Lightweight quick-dry beach shorts perfect for summer and beach activities. Bright colorful patterns with elastic waist.",
        "colors": ["blue", "tropical", "multi"],
        "sizes": ["S", "M", "L", "XL"],
        "style_tags": ["beach", "summer", "casual", "colorful", "vacation"],
        "season": "summer",
        "occasion": "beach"
    },
    {
        "id": "bottom_005",
        "name": "Women's High Waist Jeans",
        "category": "bottom",
        "price": 1199.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/51UDEzMJVpL._AC_UL640_QL65_ML3_.jpg",
        "buy_url": "https://example.com/products/bottom_005",
        "brand": "Generic",
        "description": "Trendy high waist skinny jeans for women. Stretchy comfortable fit with classic blue denim wash.",
        "colors": ["blue", "black", "white"],
        "sizes": ["24", "26", "28", "30", "32"],
        "style_tags": ["trendy", "casual", "skinny", "modern"],
        "season": "all",
        "occasion": "casual"
    },
    {
        "id": "bottom_006",
        "name": "Adidas Training Shorts",
        "category": "bottom",
        "price": 699.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/61pHAEJ4NML._AC_UX679_.jpg",
        "buy_url": "https://example.com/products/bottom_006",
        "brand": "Adidas",
        "description": "Athletic training shorts with moisture-wicking fabric. Perfect for gym workouts and running.",
        "colors": ["black", "grey", "navy"],
        "sizes": ["S", "M", "L", "XL"],
        "style_tags": ["sport", "athletic", "workout", "performance"],
        "season": "all",
        "occasion": "gym"
    },
    {
        "id": "bottom_007",
        "name": "Women's Floral Maxi Skirt",
        "category": "bottom",
        "price": 899.0,
        "currency": "INR",
        "image_url": "https://fakestoreapi.com/img/71z3kpMAYsL._AC_UY879_.jpg",
        "buy_url": "https://example.com/products/bottom_007",
        "brand": "Generic",
        "description": "Beautiful floral print maxi skirt perfect for beach parties and summer events. Flowy and comfortable.",
        "colors": ["floral", "multi", "colorful"],
        "sizes": ["S", "M", "L"],
        "style_tags": ["beach", "party", "summer", "floral", "feminine"],
        "season": "summer",
        "occasion": "party"
    }
]

print(f"\nAdding {len(bottom_products)} bottom products to database...\n")

db = SessionLocal()
try:
    added_count = 0
    
    for product_data in bottom_products:
        # Check if already exists
        existing = db.query(Product).filter(Product.id == product_data["id"]).first()
        if existing:
            print(f"⏭️  Skipping {product_data['id']} - already exists")
            continue
        
        # Generate embedding
        text_for_embedding = f"{product_data['name']} {product_data['description']}"
        embedding = embedding_model.encode(text_for_embedding).tolist()
        
        # Create product
        product = Product(
            id=product_data["id"],
            name=product_data["name"],
            category=product_data["category"],
            price=product_data["price"],
            currency=product_data["currency"],
            image_url=product_data["image_url"],
            buy_url=product_data["buy_url"],
            brand=product_data["brand"],
            description=product_data["description"],
            colors=product_data["colors"],
            sizes=product_data["sizes"],
            style_tags=product_data["style_tags"],
            season=product_data["season"],
            occasion=product_data["occasion"],
            embedding=embedding,
            is_active=True
        )
        
        db.add(product)
        added_count += 1
        print(f"✅ Added: {product_data['name']}")
    
    db.commit()
    
    # Verify
    total_products = db.query(Product).count()
    total_tops = db.query(Product).filter(Product.category == "top").count()
    total_bottoms = db.query(Product).filter(Product.category == "bottom").count()
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully added {added_count} bottom products!")
    print(f"\n📊 Database Summary:")
    print(f"   Total products: {total_products}")
    print(f"   Tops: {total_tops}")
    print(f"   Bottoms: {total_bottoms}")
    print(f"{'='*80}\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
