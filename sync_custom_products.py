"""
Sync products from our custom Product API
"""
import sys
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer

# Set environment to use SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./backend/outfit_planner.db'
sys.path.append('backend')

from app.database import Product

# Create SQLite engine
engine = create_engine('sqlite:///./backend/outfit_planner.db')
SessionLocal = sessionmaker(bind=engine)

# API URL
CUSTOM_API_URL = "http://localhost:9000/products"

print("🔄 Starting product sync from custom API...")
print(f"📡 API URL: {CUSTOM_API_URL}\n")

# Load embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def categorize_product(title, description):
    """Categorize product as top or bottom"""
    text = f"{title} {description}".lower()
    
    # Top keywords
    top_keywords = ['shirt', 't-shirt', 'tshirt', 'top', 'blouse', 'sweater', 
                   'jacket', 'hoodie', 'sweatshirt', 'tank', 'coat', 'flannel']
    
    # Bottom keywords
    bottom_keywords = ['pants', 'jeans', 'shorts', 'skirt', 'trousers', 
                      'leggings', 'joggers', 'chinos', 'cargo', 'swim shorts']
    
    # Count matches
    top_matches = sum(1 for keyword in top_keywords if keyword in text)
    bottom_matches = sum(1 for keyword in bottom_keywords if keyword in text)
    
    # Return category with most matches
    if bottom_matches > top_matches:
        return 'bottom'
    else:
        return 'top'

try:
    # Fetch products from custom API
    print("Fetching products from custom API...")
    response = requests.get(CUSTOM_API_URL, timeout=10)
    response.raise_for_status()
    products = response.json()
    
    print(f"✅ Fetched {len(products)} products\n")
    
    db = SessionLocal()
    
    # Clear existing products
    print("🗑️  Clearing old products...")
    db.query(Product).delete()
    db.commit()
    
    added_tops = 0
    added_bottoms = 0
    
    for prod in products:
        # Categorize
        category = categorize_product(prod['title'], prod['description'])
        
        # Generate embedding
        text_for_embedding = f"{prod['title']} {prod['description']}"
        embedding = embedding_model.encode(text_for_embedding).tolist()
       
        # Extract style tags and metadata
        style_tags = []
        if 'casual' in prod['description'].lower():
            style_tags.append('casual')
        if 'formal' in prod['description'].lower() or 'business' in prod['description'].lower():
            style_tags.append('formal')
        if 'beach' in prod['description'].lower() or 'summer' in prod['description'].lower():
            style_tags.append('beach')
            style_tags.append('summer')
        if 'athletic' in prod['description'].lower() or 'sport' in prod['description'].lower():
            style_tags.append('sport')
            style_tags.append('athletic')
        
        # Determine season
        season = 'all'
        if 'winter' in prod['description'].lower():
            season = 'winter'
        elif 'summer' in prod['description'].lower() or 'beach' in prod['description'].lower():
            season = 'summer'
        
        # Determine occasion
        occasion = 'casual'
        if 'formal' in prod['description'].lower() or 'business' in prod['description'].lower():
            occasion = 'formal'
        elif 'beach' in prod['description'].lower():
            occasion = 'beach'
        elif 'athletic' in prod['description'].lower() or 'gym' in prod['description'].lower():
            occasion = 'gym'
        elif 'party' in prod['description'].lower():
            occasion = 'party'
        
        # Create product
        product = Product(
            id=str(prod['id']),
            name=prod['title'],
            category=category,
            price=float(prod['price']),
            currency='INR',
            image_url=prod['image'],
            buy_url=f"https://example.com/products/{prod['id']}",
            brand='Generic',
            description=prod['description'],
            colors=['multi'],
            sizes=['S', 'M', 'L', 'XL'],
            style_tags=style_tags if style_tags else ['casual'],
            season=season,
            occasion=occasion,
            embedding=embedding,
            is_active=True
        )
        
        db.add(product)
        
        if category == 'top':
            added_tops += 1
        else:
            added_bottoms += 1
        
        print(f"✅ Added: {prod['title'][:50]} ({category})")
    
    db.commit()
    
    print(f"\n{'='*80}")
    print(f"🎉 Sync completed successfully!")
    print(f"\n📊 Summary:")
    print(f"   Total products: {len(products)}")
    print(f"   Tops: {added_tops}")
    print(f"   Bottoms: {added_bottoms}")
    print(f"{'='*80}\n")
    
except requests.exceptions.ConnectionError:
    print(f"❌ Error: Could not connect to custom API at {CUSTOM_API_URL}")
    print(f"   Make sure the product API server is running!")
    print(f"   Run: python backend/product_api_server.py")
except Exception as e:
    print(f"❌ Error during sync: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
