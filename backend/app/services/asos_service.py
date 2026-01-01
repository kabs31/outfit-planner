"""
ASOS API Service - Real-time fashion product browsing
Uses RapidAPI ASOS endpoint for live product data
API: https://rapidapi.com/api/asos10
"""
import httpx
import logging
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ASOSService:
    """Service for fetching real products from ASOS via RapidAPI"""
    
    BASE_URL = "https://asos10.p.rapidapi.com/api/v1"
    
    def __init__(self):
        self.api_key = settings.RAPIDAPI_KEY
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "asos10.p.rapidapi.com"
        }
        # Fetch products from US store (better availability)
        self.default_params = {
            "currency": "USD",
            "country": "US", 
            "store": "US",
            "languageShort": "en",
            "sizeSchema": "US"
        }
        # But redirect to INDIA website for purchase (auto-converts currency)
        self.product_base_url = "https://www.asos.com/in"
        
        # USD to INR conversion rate (approximate)
        self.usd_to_inr = 83.0
    
    async def search_products(
        self,
        query: str,
        category: str = "all",
        limit: int = 10,
        sort: str = "recommended",
        gender: str = "women"
    ) -> List[Dict]:
        """
        Search for products on ASOS by search term
        
        Args:
            query: Search query (e.g., "summer dress", "casual top")
            category: Product category for our internal use
            limit: Max products to return
            sort: Sort order (recommended, freshness, priceAsc, priceDesc)
            gender: 'men' or 'women' for filtering
            
        Returns:
            List of product dictionaries
        """
        if not self.api_key:
            logger.warning("RapidAPI key not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    **self.default_params,
                    "searchTerm": query,
                    "limit": str(limit),
                    "offset": "0",
                    "sort": sort
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/getProductListBySearchTerm",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"ASOS API error: {response.status_code} - {response.text[:200]}")
                    return []
                
                data = response.json()
                
                # Extract products from response
                products = []
                if isinstance(data, dict):
                    products = data.get("data", {}).get("products", [])
                    if not products:
                        products = data.get("products", [])
                
                logger.info(f"Found {len(products)} ASOS products for: {query}")
                
                # Transform and filter by gender
                transformed = self._transform_products(products, category)
                filtered = self._filter_by_gender(transformed, gender)
                logger.info(f"After gender filter ({gender}): {len(filtered)} products")
                return filtered
                
        except Exception as e:
            logger.error(f"ASOS API request failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_tops(self, query: str = "", limit: int = 10, gender: str = "women") -> List[Dict]:
        """Get top/shirt products"""
        if gender == "men":
            search_query = f"mens {query} shirt".strip()
        else:
            search_query = f"womens {query} top".strip()
        return await self.search_products(search_query, category="top", limit=limit, gender=gender)
    
    async def get_bottoms(self, query: str = "", limit: int = 10, gender: str = "women") -> List[Dict]:
        """Get bottom/pants products"""
        if gender == "men":
            search_query = f"mens {query} jeans pants".strip()
        else:
            search_query = f"womens {query} pants jeans".strip()
        return await self.search_products(search_query, category="bottom", limit=limit, gender=gender)
    
    async def get_dresses(self, query: str = "", limit: int = 10, gender: str = "women") -> List[Dict]:
        """Get dress products"""
        search_query = f"{gender} {query} dress".strip()
        return await self.search_products(search_query, category="dress", limit=limit)
    
    def _filter_by_gender(self, products: List[Dict], gender: str) -> List[Dict]:
        """Filter out products that don't match the specified gender - strict filtering"""
        if gender == "men":
            # For men's products, exclude women/ladies/girls/dresses/skirts
            exclude_keywords = [
                "women", "woman", "womens", "ladies", "girl", "girls",
                "dress", "dresses", "skirt", "skirts", "blouse", "bra", 
                "lingerie", "maternity", "female", "feminine"
            ]
            # Must include men keywords (strict requirement)
            include_keywords = ["men", "mens", "man", "male", "gentleman"]
        else:
            # For women's products, exclude men/boys
            exclude_keywords = ["men", "mans", "mens", "boy", "boys", "male", "gentleman"]
            include_keywords = []  # No strict requirement for women
        
        filtered = []
        for product in products:
            name = product.get("name", "").lower()
            description = (product.get("description", "") or "").lower()
            full_text = name + " " + description
            
            # Check if it has excluded keywords
            has_excluded = any(keyword in full_text for keyword in exclude_keywords)
            
            # For men, require men keywords (strict)
            if gender == "men":
                has_men_keyword = any(keyword in full_text for keyword in include_keywords)
                if has_excluded or not has_men_keyword:
                    continue
            else:
                # For women, just exclude men products
                if has_excluded:
                    continue
            
            filtered.append(product)
        
        return filtered
    
    def _transform_products(self, products: List[Dict], category: str) -> List[Dict]:
        """Transform ASOS API response to our product format"""
        transformed = []
        
        for product in products:
            try:
                # Get product ID
                product_id = str(product.get("id", ""))
                
                # Get name
                name = product.get("name", "Fashion Item")
                
                # Get price
                price_info = product.get("price", {})
                if isinstance(price_info, dict):
                    current_price = price_info.get("current", {})
                    if isinstance(current_price, dict):
                        price = float(current_price.get("value", 0))
                    else:
                        price = float(current_price) if current_price else 0
                else:
                    price = float(price_info) if price_info else 0
                
                # Get image URL
                image_url = product.get("imageUrl", "")
                if not image_url:
                    image_url = product.get("image", "")
                
                # ASOS images need https:// prefix
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://{image_url}"
                
                # Build product URL for ASOS India
                product_url = product.get("url", "")
                if product_url and not product_url.startswith("http"):
                    # Ensure URL starts with /
                    if not product_url.startswith("/"):
                        product_url = f"/{product_url}"
                    product_url = f"{self.product_base_url}{product_url}"
                elif not product_url:
                    product_url = f"{self.product_base_url}/prd/{product_id}"
                
                # Get brand
                brand = product.get("brandName", "ASOS")
                
                # Get color
                color = product.get("colour", "")
                
                if not image_url:
                    logger.warning(f"Skipping ASOS product {product_id} - no image")
                    continue
                
                # Convert USD to INR
                price_inr = round(price * self.usd_to_inr, 2)
                
                transformed.append({
                    "id": product_id,
                    "name": name,
                    "category": category,
                    "price": price_inr,
                    "currency": "INR",
                    "image_url": image_url,
                    "buy_url": product_url,
                    "brand": brand,
                    "description": name,
                    "colors": [color] if color else [],
                    "sizes": [],
                    "source": "asos"
                })
                
            except Exception as e:
                logger.warning(f"Failed to transform ASOS product: {e}")
                continue
        
        return transformed
    
    async def browse_fashion(
        self,
        prompt: str,
        num_tops: int = 5,
        num_bottoms: int = 5,
        gender: str = "women"
    ) -> Dict[str, List[Dict]]:
        """
        Browse fashion based on a prompt
        
        Args:
            prompt: Fashion prompt (e.g., "casual summer outfit")
            num_tops: Number of tops to fetch
            num_bottoms: Number of bottoms to fetch
            gender: 'men' or 'women'
            
        Returns:
            Dictionary with 'tops' and 'bottoms' lists
        """
        logger.info(f"Browsing ASOS for: {prompt} (Gender: {gender})")
        
        import asyncio
        tops_task = self.get_tops(prompt, limit=num_tops, gender=gender)
        bottoms_task = self.get_bottoms(prompt, limit=num_bottoms, gender=gender)
        
        tops, bottoms = await asyncio.gather(tops_task, bottoms_task)
        
        return {
            "tops": tops,
            "bottoms": bottoms,
            "source": "asos",
            "query": prompt,
            "gender": gender
        }


# Global instance
asos_service = ASOSService()

