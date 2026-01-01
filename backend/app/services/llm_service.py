"""
LLM Service - AI Prompt Understanding
Uses Groq Cloud API with Llama 3.1 for natural language processing
FREE tier: 14,400 requests/day
"""
import json
import re
import httpx
from typing import Dict, Optional
from app.config import settings
from app.models import ParsedPrompt
import logging

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMService:
    """Service for AI prompt understanding using Groq Cloud"""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.is_configured = bool(self.api_key)
        
        if not self.is_configured:
            logger.warning("⚠️  GROQ_API_KEY not set - will use fallback parser")
        else:
            logger.info(f"✅ Groq LLM configured with model: {self.model}")
    
    async def parse_outfit_prompt(self, prompt: str) -> ParsedPrompt:
        """
        Parse user prompt and extract outfit attributes using Groq
        
        Args:
            prompt: User's natural language prompt
            
        Returns:
            ParsedPrompt: Structured data extracted from prompt
        """
        # If Groq not configured, use fallback
        if not self.is_configured:
            logger.info("Using fallback parser (Groq not configured)")
            return self._fallback_parse(prompt)
        
        try:
            # Prepare system prompt
            system_prompt = """You are an AI fashion assistant. Analyze outfit prompts and extract structured information.

Extract the following from the user's prompt:
- mood: emotional tone (relaxed, energetic, confident, etc.)
- location: where they'll wear it (beach, office, party, gym, etc.)
- occasion: the event type (casual, formal, party, business, date, etc.)
- style: fashion style (casual, formal, streetwear, bohemian, etc.)
- colors: color preferences (bright, dark, pastel, specific colors)
- season: time of year (summer, winter, spring, fall, all-season)
- formality: level of formality (casual, semi-formal, formal)
- keywords: key fashion terms mentioned

Respond ONLY with valid JSON. No other text.

Example input: "Beach party, colorful and relaxed"
Example output:
{
  "mood": "relaxed",
  "location": "beach",
  "occasion": "party",
  "style": "casual",
  "colors": ["colorful", "bright"],
  "season": "summer",
  "formality": "casual",
  "keywords": ["beach", "party", "colorful", "relaxed", "summer"]
}"""
            
            # Call Groq API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Analyze this outfit prompt: {prompt}"}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Groq API error: {response.status_code} - {response.text}")
                    return self._fallback_parse(prompt)
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
            
            # Extract JSON from response
            parsed_data = self._extract_json(content)
            
            # Create ParsedPrompt object
            parsed_prompt = ParsedPrompt(
                original_prompt=prompt,
                mood=parsed_data.get('mood'),
                location=parsed_data.get('location'),
                occasion=parsed_data.get('occasion'),
                style=parsed_data.get('style'),
                colors=parsed_data.get('colors', []),
                season=parsed_data.get('season'),
                formality=parsed_data.get('formality'),
                keywords=parsed_data.get('keywords', [])
            )
            
            logger.info(f"✅ Parsed prompt via Groq: {parsed_prompt.dict()}")
            return parsed_prompt
            
        except Exception as e:
            logger.error(f"❌ Failed to parse prompt with Groq: {e}")
            return self._fallback_parse(prompt)
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response (handles various formats)"""
        try:
            return json.loads(text)
        except:
            # Try to find JSON in text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            logger.warning(f"Could not extract JSON from: {text[:100]}")
            return {}
    
    def _fallback_parse(self, prompt: str) -> ParsedPrompt:
        """Fallback parser using simple keyword matching"""
        prompt_lower = prompt.lower()
        
        # Simple keyword extraction
        keywords = [word for word in prompt_lower.split() if len(word) > 3]
        
        # Detect mood
        mood = None
        mood_map = {
            'relaxed': ['relaxed', 'chill', 'calm', 'easy', 'comfortable'],
            'energetic': ['energetic', 'active', 'dynamic', 'lively', 'sporty'],
            'confident': ['confident', 'bold', 'powerful', 'strong'],
            'romantic': ['romantic', 'soft', 'elegant', 'date']
        }
        for m, words in mood_map.items():
            if any(w in prompt_lower for w in words):
                mood = m
                break
        
        # Detect location
        location = None
        locations = ['beach', 'office', 'gym', 'party', 'home', 'outdoor', 'indoor', 'restaurant', 'club']
        for loc in locations:
            if loc in prompt_lower:
                location = loc
                break
        
        # Detect occasion
        occasion = None
        occasions = ['party', 'wedding', 'date', 'meeting', 'casual', 'formal', 'business', 'interview', 'dinner']
        for occ in occasions:
            if occ in prompt_lower:
                occasion = occ
                break
        
        # Detect colors
        colors = []
        color_words = ['blue', 'red', 'green', 'yellow', 'black', 'white', 'gray', 'grey', 'pink', 
                      'colorful', 'bright', 'dark', 'pastel', 'neutral', 'navy', 'beige', 'brown']
        colors = [c for c in color_words if c in prompt_lower]
        
        # Detect season
        season = None
        seasons = ['summer', 'winter', 'spring', 'fall', 'autumn']
        for s in seasons:
            if s in prompt_lower:
                season = s
                break
        
        # Detect formality
        formality = 'casual'  # default
        if any(w in prompt_lower for w in ['formal', 'business', 'professional', 'suit', 'elegant']):
            formality = 'formal'
        elif any(w in prompt_lower for w in ['semi-formal', 'smart', 'dressy']):
            formality = 'semi-formal'
        
        # Detect style
        style = formality
        style_map = {
            'streetwear': ['streetwear', 'street', 'urban', 'hip-hop'],
            'bohemian': ['boho', 'bohemian', 'hippie', 'flowy'],
            'minimalist': ['minimal', 'minimalist', 'simple', 'clean'],
            'preppy': ['preppy', 'prepster', 'ivy'],
            'sporty': ['sporty', 'athletic', 'gym', 'workout']
        }
        for s, words in style_map.items():
            if any(w in prompt_lower for w in words):
                style = s
                break
        
        logger.info(f"✅ Fallback parse completed for: {prompt}")
        
        return ParsedPrompt(
            original_prompt=prompt,
            mood=mood,
            location=location,
            occasion=occasion,
            style=style,
            colors=colors,
            season=season,
            formality=formality,
            keywords=keywords
        )
    
    def generate_search_query(self, parsed_prompt: ParsedPrompt) -> str:
        """
        Generate optimized search query from parsed prompt
        
        Args:
            parsed_prompt: Parsed prompt data
            
        Returns:
            Optimized search query string
        """
        query_parts = []
        
        if parsed_prompt.location:
            query_parts.append(parsed_prompt.location)
        if parsed_prompt.occasion:
            query_parts.append(parsed_prompt.occasion)
        if parsed_prompt.style:
            query_parts.append(parsed_prompt.style)
        if parsed_prompt.colors:
            query_parts.extend(parsed_prompt.colors[:2])
        if parsed_prompt.season:
            query_parts.append(parsed_prompt.season)
        
        # Add top keywords
        query_parts.extend(parsed_prompt.keywords[:3])
        
        # Remove duplicates and join
        unique_parts = list(dict.fromkeys(query_parts))
        query = " ".join(unique_parts)
        
        logger.info(f"Generated search query: {query}")
        return query
    
    async def classify_product_gender(
        self,
        products: list,
        target_gender: str
    ) -> list:
        """
        Use LLM to classify products by gender
        
        Args:
            products: List of product dicts with name, description, category, etc.
            target_gender: 'men' or 'women' - filter to only return products for this gender
            
        Returns:
            List of products that match the target gender
        """
        if not self.is_configured:
            logger.warning("Groq not configured - using keyword fallback for gender filtering")
            return self._fallback_gender_filter(products, target_gender)
        
        if not products:
            return []
        
        try:
            # Batch products for efficiency (process up to 10 at a time)
            batch_size = 10
            filtered_products = []
            
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                
                # Prepare product data for LLM
                product_data = []
                for p in batch:
                    product_data.append({
                        "name": p.get("name", ""),
                        "description": p.get("description", ""),
                        "category": p.get("category", ""),
                        "brand": p.get("brand", "")
                    })
                
                # Create prompt for LLM
                system_prompt = f"""You are a fashion product classifier. Determine if each product is for MEN or WOMEN.

Target gender: {target_gender.upper()}

For each product, analyze:
- Product name/title
- Description
- Category
- Brand

Return ONLY products that are clearly for {target_gender.upper()}.

Rules:
- If product is unisex/gender-neutral, include it ONLY if it's commonly worn by {target_gender}
- Exclude products explicitly for the opposite gender
- Dresses, skirts, blouses are typically WOMEN
- Men's suits, ties, men's jeans are typically MEN

Respond with JSON array of indices (0-based) of products that match {target_gender.upper()}.
Example: [0, 2, 4] means products at indices 0, 2, and 4 match.

Return ONLY the JSON array, no other text."""
                
                user_prompt = f"Products to classify:\n{json.dumps(product_data, indent=2)}\n\nReturn array of indices for {target_gender.upper()} products:"
                
                # Call Groq API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.1,  # Low temperature for consistent classification
                            "max_tokens": 200
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Groq API error for gender classification: {response.status_code}")
                        # Fallback to keyword filtering for this batch
                        filtered_products.extend(self._fallback_gender_filter(batch, target_gender))
                        continue
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Extract indices from response
                    try:
                        # Try to extract JSON array from response
                        parsed_data = self._extract_json(content)
                        
                        # Handle different response formats
                        if isinstance(parsed_data, list):
                            indices = parsed_data
                        elif isinstance(parsed_data, dict) and "indices" in parsed_data:
                            indices = parsed_data["indices"]
                        elif isinstance(parsed_data, dict) and "products" in parsed_data:
                            # LLM might return product objects instead of indices
                            # In this case, use fallback
                            indices = []
                        else:
                            indices = []
                        
                        if isinstance(indices, list) and len(indices) > 0:
                            # Add products at those indices
                            for idx in indices:
                                if isinstance(idx, int) and 0 <= idx < len(batch):
                                    filtered_products.append(batch[idx])
                        else:
                            # If no valid indices, use fallback
                            filtered_products.extend(self._fallback_gender_filter(batch, target_gender))
                    except Exception as e:
                        # Fallback if JSON parsing fails
                        logger.warning(f"Could not parse LLM response: {content[:100]} - Error: {e}")
                        filtered_products.extend(self._fallback_gender_filter(batch, target_gender))
            
            logger.info(f"✅ LLM filtered {len(products)} products → {len(filtered_products)} for {target_gender}")
            return filtered_products
            
        except Exception as e:
            logger.error(f"❌ LLM gender classification failed: {e}")
            # Fallback to keyword filtering
            return self._fallback_gender_filter(products, target_gender)
    
    def _fallback_gender_filter(self, products: list, target_gender: str) -> list:
        """Fallback keyword-based gender filtering"""
        if target_gender == "men":
            exclude_keywords = [
                "women", "woman", "womens", "ladies", "girl", "girls",
                "dress", "dresses", "skirt", "skirts", "blouse", "bra",
                "lingerie", "maternity", "female", "feminine"
            ]
            include_keywords = ["men", "mens", "man", "male", "gentleman"]
        else:
            exclude_keywords = ["men", "mans", "mens", "boy", "boys", "male", "gentleman"]
            include_keywords = []
        
        filtered = []
        for product in products:
            name = (product.get("name", "") or "").lower()
            description = (product.get("description", "") or "").lower()
            full_text = name + " " + description
            
            has_excluded = any(kw in full_text for kw in exclude_keywords)
            
            if target_gender == "men":
                has_men_keyword = any(kw in full_text for kw in include_keywords)
                if not has_excluded and has_men_keyword:
                    filtered.append(product)
            else:
                if not has_excluded:
                    filtered.append(product)
        
        return filtered
    
    async def health_check(self) -> Dict[str, str]:
        """Check if LLM service is healthy"""
        if not self.is_configured:
            return {"status": "fallback", "message": "Using keyword parser (Groq not configured)"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 5
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"status": "healthy", "model": self.model, "provider": "Groq"}
                else:
                    return {"status": "unhealthy", "error": f"API returned {response.status_code}"}
                    
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
llm_service = LLMService()


# ==================== TESTING ====================

if __name__ == "__main__":
    import asyncio
    
    test_prompts = [
        "Beach party, colorful and relaxed",
        "Business meeting, professional and confident",
        "Casual date night, romantic and elegant",
        "Gym workout, comfortable and sporty"
    ]
    
    async def test():
        service = LLMService()
        
        print("Testing LLM Service (Groq)...")
        print("=" * 60)
        
        for prompt in test_prompts:
            print(f"\n📝 Prompt: {prompt}")
            print("-" * 60)
            
            parsed = await service.parse_outfit_prompt(prompt)
            print(f"🎯 Parsed:")
            print(f"  Mood: {parsed.mood}")
            print(f"  Location: {parsed.location}")
            print(f"  Occasion: {parsed.occasion}")
            print(f"  Style: {parsed.style}")
            print(f"  Colors: {parsed.colors}")
            print(f"  Season: {parsed.season}")
            print(f"  Formality: {parsed.formality}")
            print(f"  Keywords: {parsed.keywords}")
            
            query = service.generate_search_query(parsed)
            print(f"🔍 Search Query: {query}")
        
        print("\n" + "=" * 60)
        health = await service.health_check()
        print(f"Health check: {health}")
    
    asyncio.run(test())

