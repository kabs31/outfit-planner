"""
Product Service - Product search, matching, and combination
Uses vector embeddings for semantic search
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sentence_transformers import SentenceTransformer
import numpy as np
import httpx
import logging

from app.config import settings
from app.models import ProductItem, OutfitCombination, ParsedPrompt, ClothingCategory
from app.database import Product

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product search and outfit combination"""
    
    def __init__(self):
        # Load embedding model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("✅ Embedding model loaded")
    
    # ==================== PRODUCT FETCHING ====================
    
    async def fetch_products_from_api(self) -> List[Dict]:
        """
        Fetch products from external API (FakeStoreAPI for now)
        In production, replace with real e-commerce APIs
        """
        try:
            async with httpx.AsyncClient() as client:
                # Fetch from FakeStoreAPI
                response = await client.get(
                    f"{settings.FAKE_STORE_API}/products/category/men's clothing",
                    timeout=10.0
                )
                mens_products = response.json()
                
                response = await client.get(
                    f"{settings.FAKE_STORE_API}/products/category/women's clothing",
                    timeout=10.0
                )
                womens_products = response.json()
                
                all_products = mens_products + womens_products
                logger.info(f"✅ Fetched {len(all_products)} products from API")
                return all_products
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch products from API: {e}")
            return []
    
    def categorize_product(self, product_data: Dict) -> str:
        """
        Categorize product as top or bottom based on title/description
        """
        title_lower = product_data.get('title', '').lower()
        
        # Top indicators
        top_keywords = ['shirt', 't-shirt', 'tshirt', 'top', 'blouse', 'sweater', 
                       'jacket', 'hoodie', 'sweatshirt', 'tank']
        
        # Bottom indicators
        bottom_keywords = ['pants', 'jeans', 'shorts', 'skirt', 'trousers', 
                          'leggings', 'joggers']
        
        # Check for keywords
        for keyword in top_keywords:
            if keyword in title_lower:
                return 'top'
        
        for keyword in bottom_keywords:
            if keyword in title_lower:
                return 'bottom'
        
        # Default: assume top if uncertain
        return 'top'
    
    def convert_api_product_to_model(self, api_product: Dict) -> ProductItem:
        """Convert API product format to our ProductItem model"""
        category = self.categorize_product(api_product)
        
        return ProductItem(
            id=str(api_product['id']),
            name=api_product['title'],
            category=ClothingCategory(category),
            price=float(api_product['price']) * 80,  # Convert USD to INR (approx)
            currency="INR",
            image_url=api_product['image'],
            buy_url=f"{settings.FAKE_STORE_API}/products/{api_product['id']}",
            brand=api_product.get('brand', 'Generic'),
            description=api_product.get('description', ''),
            colors=None,  # API doesn't provide
            sizes=None    # API doesn't provide
        )
    
    async def sync_products_to_db(self, db: Session) -> int:
        """
        Fetch products from API and sync to database with embeddings
        
        Returns:
            Number of products synced
        """
        try:
            # Fetch from API
            api_products = await self.fetch_products_from_api()
            synced_count = 0
            
            for api_product in api_products:
                try:
                    product_id = str(api_product['id'])
                    
                    # Check if already exists
                    existing = db.query(Product).filter(Product.id == product_id).first()
                    if existing:
                        continue
                    
                    # Convert to our model
                    product_model = self.convert_api_product_to_model(api_product)
                    category = self.categorize_product(api_product)
                    
                    # Generate embedding
                    text_for_embedding = f"{product_model.name} {product_model.description}"
                    embedding = self.embedding_model.encode(text_for_embedding).tolist()
                    
                    # Create database record
                    db_product = Product(
                        id=product_model.id,
                        name=product_model.name,
                        category=category,
                        price=product_model.price,
                        currency=product_model.currency,
                        image_url=str(product_model.image_url),
                        buy_url=str(product_model.buy_url),
                        brand=product_model.brand,
                        description=product_model.description,
                        embedding=embedding,
                        is_active=True
                    )
                    
                    db.add(db_product)
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync product {api_product.get('id')}: {e}")
                    continue
            
            db.commit()
            logger.info(f"✅ Synced {synced_count} products to database")
            return synced_count
            
        except Exception as e:
            logger.error(f"❌ Failed to sync products: {e}")
            db.rollback()
            return 0
    
    # ==================== SEMANTIC SEARCH ====================
    
    def search_products(
        self,
        db: Session,
        query: str,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 10
    ) -> List[ProductItem]:
        """
        Semantic search for products using vector similarity
        
        Args:
            db: Database session
            query: Search query text
            category: Filter by category (top/bottom)
            max_price: Maximum price filter
            limit: Max results to return
            
        Returns:
            List of matching products
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Build base query
            db_query = db.query(Product).filter(Product.is_active == True)
            
            # Apply filters
            if category:
                db_query = db_query.filter(Product.category == category)
            if max_price:
                db_query = db_query.filter(Product.price <= max_price)
            
            # Get all matching products
            products = db_query.all()
            
            if not products:
                logger.warning(f"No products found for query: {query}")
                return []
            
            # Calculate cosine similarity
            product_scores = []
            for product in products:
                if product.embedding:
                    # Cosine similarity
                    similarity = np.dot(query_embedding, product.embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(product.embedding)
                    )
                    product_scores.append((product, similarity))
            
            # Sort by similarity
            product_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Convert top results to ProductItem
            results = []
            for product, score in product_scores[:limit]:
                results.append(ProductItem(
                    id=product.id,
                    name=product.name,
                    category=ClothingCategory(product.category),
                    price=product.price,
                    currency=product.currency,
                    image_url=product.image_url,
                    buy_url=product.buy_url,
                    brand=product.brand,
                    description=product.description,
                    colors=product.colors,
                    sizes=product.sizes
                ))
            
            logger.info(f"✅ Found {len(results)} products for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    # ==================== OUTFIT COMBINATION ====================
    
    def create_outfit_combinations(
        self,
        tops: List[ProductItem],
        bottoms: List[ProductItem],
        max_combinations: int = 5
    ) -> List[OutfitCombination]:
        """
        Create outfit combinations from tops and bottoms
        
        Args:
            tops: List of top products
            bottoms: List of bottom products
            max_combinations: Maximum combinations to create
            
        Returns:
            List of outfit combinations with match scores
        """
        combinations = []
        
        # Create all possible combinations
        for top in tops[:3]:  # Top 3 tops
            for bottom in bottoms[:3]:  # Top 3 bottoms
                # Calculate match score based on price similarity and other factors
                price_diff = abs(top.price - bottom.price)
                max_price = max(top.price, bottom.price)
                price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 0.5
                
                # Simple match score (can be improved with ML)
                match_score = price_similarity * 0.6 + 0.4  # Baseline 0.4
                
                combination = OutfitCombination(
                    top=top,
                    bottom=bottom,
                    total_price=top.price + bottom.price,
                    match_score=min(match_score, 1.0),
                    style_tags=[]
                )
                combinations.append(combination)
        
        # Sort by match score
        combinations.sort(key=lambda x: x.match_score, reverse=True)
        
        # Return top combinations
        result = combinations[:max_combinations]
        logger.info(f"✅ Created {len(result)} outfit combinations")
        return result
    
    def find_matching_outfits(
        self,
        db: Session,
        parsed_prompt: ParsedPrompt,
        max_price: Optional[float] = None,
        num_outfits: int = 3
    ) -> List[OutfitCombination]:
        """
        Find matching outfits based on parsed prompt
        
        Args:
            db: Database session
            parsed_prompt: Parsed user prompt
            max_price: Maximum total price
            num_outfits: Number of outfits to return
            
        Returns:
            List of outfit combinations
        """
        try:
            # Create search query
            search_query = " ".join([
                parsed_prompt.mood or "",
                parsed_prompt.location or "",
                parsed_prompt.occasion or "",
                parsed_prompt.style or "",
                " ".join(parsed_prompt.colors or []),
                " ".join(parsed_prompt.keywords or [])
            ]).strip()
            
            # Calculate per-item price limit if total max specified
            item_max_price = (max_price / 2) if max_price else None
            
            # Search for tops
            tops = self.search_products(
                db=db,
                query=search_query,
                category="top",
                max_price=item_max_price,
                limit=5
            )
            
            # Search for bottoms
            bottoms = self.search_products(
                db=db,
                query=search_query,
                category="bottom",
                max_price=item_max_price,
                limit=5
            )
            
            if not tops or not bottoms:
                logger.warning("No matching tops or bottoms found")
                return []
            
            # Create combinations
            combinations = self.create_outfit_combinations(
                tops=tops,
                bottoms=bottoms,
                max_combinations=num_outfits
            )
            
            # Filter by total price if specified
            if max_price:
                combinations = [c for c in combinations if c.total_price <= max_price]
            
            return combinations
            
        except Exception as e:
            logger.error(f"❌ Failed to find matching outfits: {e}")
            return []


# Global instance
product_service = ProductService()


# ==================== TESTING ====================

if __name__ == "__main__":
    # Test the service
    import asyncio
    from app.database import SessionLocal
    from app.services.llama_service import llama_service
    
    async def test():
        db = SessionLocal()
        service = ProductService()
        
        print("=" * 60)
        print("Testing Product Service")
        print("=" * 60)
        
        # Test 1: Sync products
        print("\n1. Syncing products from API...")
        count = await service.sync_products_to_db(db)
        print(f"✅ Synced {count} products")
        
        # Test 2: Search products
        print("\n2. Searching for products...")
        tops = service.search_products(db, "casual shirt", category="top", limit=3)
        print(f"✅ Found {len(tops)} tops")
        for top in tops:
            print(f"  - {top.name}: ₹{top.price}")
        
        # Test 3: Create outfit
        print("\n3. Creating outfit from prompt...")
        prompt = "Beach party, colorful and relaxed"
        parsed = llama_service.parse_outfit_prompt(prompt)
        outfits = service.find_matching_outfits(db, parsed, num_outfits=2)
        print(f"✅ Created {len(outfits)} outfits")
        for i, outfit in enumerate(outfits, 1):
            print(f"\n  Outfit {i}:")
            print(f"    Top: {outfit.top.name} (₹{outfit.top.price})")
            print(f"    Bottom: {outfit.bottom.name} (₹{outfit.bottom.price})")
            print(f"    Total: ₹{outfit.total_price}")
            print(f"    Match Score: {outfit.match_score:.2f}")
        
        db.close()
    
    asyncio.run(test())
