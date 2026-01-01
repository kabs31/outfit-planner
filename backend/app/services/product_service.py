"""
Product Service - Outfit combination creation
Simplified version without database - works with ASOS API results
"""
from typing import List, Optional
import logging

from app.models import ProductItem, OutfitCombination, ParsedPrompt

logger = logging.getLogger(__name__)


class ProductService:
    """Service for creating outfit combinations"""
    
    def create_outfit_combinations(
        self,
        tops: List[ProductItem],
        bottoms: List[ProductItem],
        max_combinations: int = 3
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
        
        # Create combinations (top 3 of each)
        for i, top in enumerate(tops[:3]):
            for j, bottom in enumerate(bottoms[:3]):
                # Calculate match score based on price similarity
                price_diff = abs(top.price - bottom.price)
                max_price = max(top.price, bottom.price)
                price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 0.5
                
                # Match score (price similarity + position bonus)
                position_bonus = (6 - i - j) / 6 * 0.3  # Higher for top results
                match_score = price_similarity * 0.5 + position_bonus + 0.2
                
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
        
        result = combinations[:max_combinations]
        logger.info(f"✅ Created {len(result)} outfit combinations")
        return result
    
    def create_mixed_outfit_combinations(
        self,
        tops: List[ProductItem],
        bottoms: List[ProductItem],
        max_combinations: int = 3
    ) -> List[OutfitCombination]:
        """
        Create MIXED outfit combinations prioritizing cross-store combos
        
        e.g., ASOS top + Amazon bottom, Amazon top + ASOS bottom
        
        Args:
            tops: List of top products (with store info in brand)
            bottoms: List of bottom products (with store info in brand)
            max_combinations: Maximum combinations to create
            
        Returns:
            List of outfit combinations with match scores
        """
        combinations = []
        
        def get_store(product: ProductItem) -> str:
            """Extract store name from brand field"""
            brand = product.brand or ""
            if "(ASOS)" in brand:
                return "asos"
            elif "(AMAZON)" in brand:
                return "amazon"
            return "unknown"
        
        # Separate by store
        asos_tops = [t for t in tops if get_store(t) == "asos"]
        amazon_tops = [t for t in tops if get_store(t) == "amazon"]
        asos_bottoms = [b for b in bottoms if get_store(b) == "asos"]
        amazon_bottoms = [b for b in bottoms if get_store(b) == "amazon"]
        
        logger.info(f"📦 Mix sources: ASOS({len(asos_tops)}T/{len(asos_bottoms)}B) + Amazon({len(amazon_tops)}T/{len(amazon_bottoms)}B)")
        
        # Priority 1: Cross-store combinations (ASOS top + Amazon bottom)
        for top in asos_tops[:2]:
            for bottom in amazon_bottoms[:2]:
                combo = self._create_combination(top, bottom, cross_store_bonus=0.1)
                combinations.append(combo)
        
        # Priority 2: Cross-store combinations (Amazon top + ASOS bottom)
        for top in amazon_tops[:2]:
            for bottom in asos_bottoms[:2]:
                combo = self._create_combination(top, bottom, cross_store_bonus=0.1)
                combinations.append(combo)
        
        # Priority 3: Same-store combinations (fallback)
        for top in asos_tops[:1]:
            for bottom in asos_bottoms[:1]:
                combo = self._create_combination(top, bottom, cross_store_bonus=0)
                combinations.append(combo)
        
        for top in amazon_tops[:1]:
            for bottom in amazon_bottoms[:1]:
                combo = self._create_combination(top, bottom, cross_store_bonus=0)
                combinations.append(combo)
        
        # Sort by match score
        combinations.sort(key=lambda x: x.match_score, reverse=True)
        
        result = combinations[:max_combinations]
        logger.info(f"✅ Created {len(result)} MIXED outfit combinations")
        return result
    
    def _create_combination(
        self,
        top: ProductItem,
        bottom: ProductItem,
        cross_store_bonus: float = 0
    ) -> OutfitCombination:
        """Helper to create a single outfit combination"""
        # Calculate match score based on price similarity
        price_diff = abs(top.price - bottom.price)
        max_price = max(top.price, bottom.price)
        price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 0.5
        
        # Base match score
        match_score = price_similarity * 0.5 + 0.3 + cross_store_bonus
        
        return OutfitCombination(
            top=top,
            bottom=bottom,
            total_price=top.price + bottom.price,
            match_score=min(match_score, 1.0),
            style_tags=["mixed" if cross_store_bonus > 0 else "single-store"]
        )


# Global instance
product_service = ProductService()
