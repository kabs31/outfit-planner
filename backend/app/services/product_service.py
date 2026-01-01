"""
Product Service - Outfit combination creation
Simplified version without database - works with ASOS API results
"""
from typing import List, Optional, Dict
import logging
import asyncio

from app.models import ProductItem, OutfitCombination, ParsedPrompt
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ProductService:
    """Service for creating outfit combinations"""
    
    async def create_outfit_combinations(
        self,
        tops: List[ProductItem],
        bottoms: List[ProductItem],
        max_combinations: int = 3,
        user_prompt: Optional[str] = None
    ) -> List[OutfitCombination]:
        """
        Create outfit combinations from tops and bottoms with LLM compatibility check
        
        Args:
            tops: List of top products
            bottoms: List of bottom products
            max_combinations: Maximum combinations to create
            user_prompt: Optional user prompt for context in compatibility check
            
        Returns:
            List of outfit combinations with match scores
        """
        combinations = []
        
        # Create all potential combinations (top 3 of each)
        potential_combos = []
        for i, top in enumerate(tops[:3]):
            for j, bottom in enumerate(bottoms[:3]):
                potential_combos.append((top, bottom, i, j))
        
        # Check compatibility for all combinations in parallel (batch)
        compatibility_tasks = []
        for top, bottom, i, j in potential_combos:
            top_dict = {
                "name": top.name,
                "description": top.description or "",
                "category": top.category or "",
                "brand": top.brand or ""
            }
            bottom_dict = {
                "name": bottom.name,
                "description": bottom.description or "",
                "category": bottom.category or "",
                "brand": bottom.brand or ""
            }
            compatibility_tasks.append(
                llm_service.check_outfit_compatibility(top_dict, bottom_dict, user_prompt)
            )
        
        # Run all compatibility checks in parallel
        compatibility_results = await asyncio.gather(*compatibility_tasks)
        
        # Create combinations with compatibility scores
        for idx, (top, bottom, i, j) in enumerate(potential_combos):
            compat_result = compatibility_results[idx]
            
            # Calculate base match score based on price similarity
            price_diff = abs(top.price - bottom.price)
            max_price = max(top.price, bottom.price)
            price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 0.5
            
            # Position bonus (higher for top results)
            position_bonus = (6 - i - j) / 6 * 0.2
            
            # Compatibility score from LLM (weighted heavily)
            compatibility_score = compat_result.get("compatibility_score", 0.5)
            compatibility_weight = 0.5  # 50% weight on compatibility
            
            # Final match score: compatibility (50%) + price similarity (30%) + position (20%)
            match_score = (
                compatibility_score * compatibility_weight +
                price_similarity * 0.3 +
                position_bonus
            )
            
            # Only include if compatible or has decent compatibility score
            if compat_result.get("compatible", True) or compatibility_score >= 0.4:
                combination = OutfitCombination(
                    top=top,
                    bottom=bottom,
                    total_price=top.price + bottom.price,
                    match_score=min(match_score, 1.0),
                    style_tags=[compat_result.get("reasoning", "")[:50]] if compat_result.get("reasoning") else []
                )
                combinations.append(combination)
        
        # Sort by match score (compatibility-weighted)
        combinations.sort(key=lambda x: x.match_score, reverse=True)
        
        result = combinations[:max_combinations]
        logger.info(f"✅ Created {len(result)} outfit combinations (LLM compatibility checked)")
        return result
    
    async def create_mixed_outfit_combinations(
        self,
        tops: List[ProductItem],
        bottoms: List[ProductItem],
        max_combinations: int = 3,
        user_prompt: Optional[str] = None
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
        
        # Collect all potential combinations
        potential_combos = []
        
        # Priority 1: Cross-store combinations (ASOS top + Amazon bottom)
        for top in asos_tops[:2]:
            for bottom in amazon_bottoms[:2]:
                potential_combos.append((top, bottom, 0.1))
        
        # Priority 2: Cross-store combinations (Amazon top + ASOS bottom)
        for top in amazon_tops[:2]:
            for bottom in asos_bottoms[:2]:
                potential_combos.append((top, bottom, 0.1))
        
        # Priority 3: Same-store combinations (fallback)
        for top in asos_tops[:1]:
            for bottom in asos_bottoms[:1]:
                potential_combos.append((top, bottom, 0))
        
        for top in amazon_tops[:1]:
            for bottom in amazon_bottoms[:1]:
                potential_combos.append((top, bottom, 0))
        
        # Check compatibility for all combinations in parallel
        compatibility_tasks = []
        for top, bottom, cross_store_bonus in potential_combos:
            top_dict = {
                "name": top.name,
                "description": top.description or "",
                "category": top.category or "",
                "brand": top.brand or ""
            }
            bottom_dict = {
                "name": bottom.name,
                "description": bottom.description or "",
                "category": bottom.category or "",
                "brand": bottom.brand or ""
            }
            compatibility_tasks.append(
                llm_service.check_outfit_compatibility(top_dict, bottom_dict, user_prompt)
            )
        
        # Run all compatibility checks in parallel
        compatibility_results = await asyncio.gather(*compatibility_tasks)
        
        # Create combinations with compatibility scores
        for idx, (top, bottom, cross_store_bonus) in enumerate(potential_combos):
            compat_result = compatibility_results[idx]
            
            # Calculate base match score
            price_diff = abs(top.price - bottom.price)
            max_price = max(top.price, bottom.price)
            price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 0.5
            
            # Compatibility score from LLM (weighted heavily)
            compatibility_score = compat_result.get("compatibility_score", 0.5)
            
            # Final match score: compatibility (50%) + price (30%) + cross-store bonus (10%) + base (10%)
            match_score = (
                compatibility_score * 0.5 +
                price_similarity * 0.3 +
                cross_store_bonus +
                0.1
            )
            
            # Only include if compatible or has decent compatibility score
            if compat_result.get("compatible", True) or compatibility_score >= 0.4:
                combo = OutfitCombination(
                    top=top,
                    bottom=bottom,
                    total_price=top.price + bottom.price,
                    match_score=min(match_score, 1.0),
                    style_tags=["mixed" if cross_store_bonus > 0 else "single-store"]
                )
                combinations.append(combo)
        
        # Sort by match score
        combinations.sort(key=lambda x: x.match_score, reverse=True)
        
        result = combinations[:max_combinations]
        logger.info(f"✅ Created {len(result)} MIXED outfit combinations (LLM compatibility checked)")
        return result


# Global instance
product_service = ProductService()
