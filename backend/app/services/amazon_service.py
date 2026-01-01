"""
Amazon Product Service - Real-time product browsing
Uses RapidAPI Amazon Search endpoint for live product data
API: https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data

Subscribe at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data
"""
import httpx
import logging
from typing import List, Dict
from app.config import settings

logger = logging.getLogger(__name__)


class AmazonService:
    """Service for fetching products from Amazon via RapidAPI Search"""
    
    # RapidAPI Amazon endpoint
    BASE_URL = "https://real-time-amazon-data.p.rapidapi.com"
    
    def __init__(self):
        self.api_key = settings.RAPIDAPI_KEY  # Same key works for multiple RapidAPI services
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
        }
        
        # Default to India store
        self.default_country = "IN"
        
        if self.api_key:
            logger.info("✅ Amazon Service configured (RapidAPI Search)")
        else:
            logger.warning("⚠️ Amazon Service: RAPIDAPI_KEY not set")
    
    async def search_products(
        self,
        query: str,
        limit: int = 10,
        sort_by: str = "BEST_SELLERS"
    ) -> List[Dict]:
        """
        Search for products on Amazon
        
        Args:
            query: Search query
            limit: Max products to return
            sort_by: Sort order (RELEVANCE, BEST_SELLERS, LOWEST_PRICE, etc.)
            
        Returns:
            List of raw product dictionaries
        """
        if not self.api_key:
            logger.warning("Amazon API key not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    params={
                        "query": query,
                        "page": "1",
                        "country": self.default_country,
                        "sort_by": sort_by,
                        "product_condition": "NEW"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Amazon Search API error: {response.status_code} - {response.text[:200]}")
                    return []
                
                data = response.json()
                
                # Extract products from response
                products = data.get("data", {}).get("products", [])
                
                if not products:
                    logger.warning(f"No Amazon products found for: {query}")
                    return []
                
                logger.info(f"Found {len(products)} Amazon products for: {query}")
                
                return products[:limit]
                
        except Exception as e:
            logger.error(f"Amazon Search API request failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_tops(self, query: str = "", limit: int = 10, gender: str = "women") -> List[Dict]:
        """Get top/shirt products from Amazon"""
        # Build search query
        if gender == "women":
            search_query = f"women top shirt kurta {query}".strip()
        else:
            search_query = f"men shirt t-shirt polo {query}".strip()
        
        products = await self.search_products(search_query, limit=limit * 2, sort_by="BEST_SELLERS")
        transformed = self._transform_products(products, "top")
        
        # Filter out wrong gender using word boundaries
        # Note: "women" contains "men", so we need careful matching
        if gender == "women":
            # For women's products, exclude items with "men's", "mens", "boys"
            exclude_patterns = [" men ", " mens ", " men's ", "for men", "boys", " boy "]
        else:
            # For men's products, exclude women/ladies/girls
            exclude_patterns = [" women ", " womens ", " women's ", "for women", "ladies", " girl", "girls"]
        
        filtered = []
        for p in transformed:
            name_lower = " " + p.get("name", "").lower() + " "  # Add spaces for word boundary matching
            has_excluded = any(pat in name_lower for pat in exclude_patterns)
            if not has_excluded:
                filtered.append(p)
        
        return filtered[:limit]
    
    async def get_bottoms(self, query: str = "", limit: int = 10, gender: str = "women") -> List[Dict]:
        """Get bottom/pants products from Amazon"""
        # Build search query
        if gender == "women":
            search_query = f"women jeans pants palazzo {query}".strip()
        else:
            search_query = f"men jeans pants trousers {query}".strip()
        
        products = await self.search_products(search_query, limit=limit * 2, sort_by="BEST_SELLERS")
        transformed = self._transform_products(products, "bottom")
        
        # Filter out wrong gender using word boundaries
        if gender == "women":
            exclude_patterns = [" men ", " mens ", " men's ", "for men", "boys", " boy "]
        else:
            exclude_patterns = [" women ", " womens ", " women's ", "for women", "ladies", " girl", "girls"]
        
        filtered = []
        for p in transformed:
            name_lower = " " + p.get("name", "").lower() + " "
            has_excluded = any(pat in name_lower for pat in exclude_patterns)
            if not has_excluded:
                filtered.append(p)
        
        return filtered[:limit]
    
    def _transform_products(self, products: List[Dict], category: str) -> List[Dict]:
        """Transform Amazon Best Sellers API response to our product format"""
        transformed = []
        
        for product in products:
            try:
                # Get ASIN (Amazon Standard Identification Number)
                asin = product.get("asin", "")
                
                # Get product title (best sellers use product_title)
                name = product.get("product_title", "") or product.get("title", "Fashion Item")
                
                # Get price - best sellers format
                price_info = product.get("product_price", "")
                if isinstance(price_info, dict):
                    price = self._parse_price(price_info.get("value", ""))
                else:
                    price = self._parse_price(price_info)
                
                # Get image URL (best sellers use product_photo)
                image_url = product.get("product_photo", "")
                if not image_url:
                    image_url = product.get("product_main_image_url", "")
                if not image_url:
                    image_url = product.get("image", "")
                
                # Get product URL
                product_url = product.get("product_url", "")
                if not product_url and asin:
                    product_url = f"https://www.amazon.in/dp/{asin}"
                
                # Skip if no image
                if not image_url:
                    continue
                
                # Get rating (best sellers format)
                rating = product.get("product_star_rating", "")
                if not rating:
                    rating = product.get("rating", "")
                
                # Get reviews count
                reviews = product.get("product_num_ratings", 0)
                if not reviews:
                    reviews = product.get("reviews_count", 0)
                
                # Get rank
                rank = product.get("rank", 0)
                
                transformed.append({
                    "id": asin,
                    "name": name[:100],  # Truncate long names
                    "category": category,
                    "price": price,
                    "currency": "INR",
                    "image_url": image_url,
                    "buy_url": product_url,
                    "brand": product.get("product_brand", "Amazon"),
                    "description": name,
                    "colors": [],
                    "sizes": [],
                    "source": "amazon",
                    "rating": rating,
                    "reviews": reviews,
                    "best_seller_rank": rank
                })
                
            except Exception as e:
                logger.warning(f"Failed to transform Amazon product: {e}")
                continue
        
        return transformed
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string like '₹1,299' or '$29.99' to float"""
        if not price_str:
            return 0.0
        
        import re
        # Remove currency symbols and extract numbers
        numbers = re.findall(r'[\d,]+\.?\d*', str(price_str))
        if numbers:
            # Take the first number found
            price_text = numbers[0].replace(',', '')
            try:
                return float(price_text)
            except ValueError:
                return 0.0
        return 0.0
    
    async def browse_fashion(
        self,
        prompt: str,
        num_tops: int = 5,
        num_bottoms: int = 5,
        gender: str = "women"
    ) -> Dict[str, List[Dict]]:
        """
        Browse Amazon fashion products sorted by Best Sellers
        
        Args:
            prompt: Fashion prompt (used to refine search)
            num_tops: Number of tops to fetch
            num_bottoms: Number of bottoms to fetch
            gender: 'men' or 'women'
            
        Returns:
            Dictionary with 'tops' and 'bottoms' lists
        """
        logger.info(f"🛒 Searching Amazon for: {gender}'s fashion ({prompt})")
        
        import asyncio
        tops_task = self.get_tops(prompt, limit=num_tops, gender=gender)
        bottoms_task = self.get_bottoms(prompt, limit=num_bottoms, gender=gender)
        
        tops, bottoms = await asyncio.gather(tops_task, bottoms_task)
        
        return {
            "tops": tops,
            "bottoms": bottoms,
            "source": "amazon",
            "query": prompt,
            "gender": gender
        }


# Global instance
amazon_service = AmazonService()

