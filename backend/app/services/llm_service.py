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

