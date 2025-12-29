"""
Llama Service - AI Prompt Understanding
Uses Ollama + Llama 3.1 8B for natural language processing
"""
import ollama
import json
import re
from typing import Dict, List, Optional
from app.config import settings
from app.models import ParsedPrompt
import logging

logger = logging.getLogger(__name__)


class LlamaService:
    """Service for AI prompt understanding using Llama 3.1"""
    
    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_HOST)
        self.model = settings.OLLAMA_MODEL
        
        # Check if model is available
        try:
            self._check_model()
        except Exception as e:
            logger.warning(f"⚠️  Llama model not ready: {e}")
    
    def _check_model(self):
        """Check if Llama model is available"""
        try:
            models = self.client.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found. Available: {model_names}")
                logger.info("Run: ollama pull llama3.1:8b-q4_0")
            else:
                logger.info(f"✅ Llama model {self.model} ready")
                
        except Exception as e:
            logger.error(f"Failed to check Llama model: {e}")
            raise
    
    def parse_outfit_prompt(self, prompt: str) -> ParsedPrompt:
        """
        Parse user prompt and extract outfit attributes
        
        Args:
            prompt: User's natural language prompt
            
        Returns:
            ParsedPrompt: Structured data extracted from prompt
        """
        try:
            # Prepare system prompt for Llama
            system_prompt = """You are an AI fashion assistant. Your job is to analyze outfit prompts and extract structured information.

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
            
            # Call Llama
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this outfit prompt: {prompt}"}
                ],
                options={
                    "temperature": 0.3,  # Lower temperature for more consistent extraction
                    "num_predict": 300   # Limit response length
                }
            )
            
            # Extract JSON from response
            content = response['message']['content']
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
            
            logger.info(f"✅ Parsed prompt: {parsed_prompt.dict()}")
            return parsed_prompt
            
        except Exception as e:
            logger.error(f"❌ Failed to parse prompt with Llama: {e}")
            # Fallback to basic keyword extraction
            return self._fallback_parse(prompt)
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from Llama response (handles various formats)"""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except:
            # Try to find JSON in text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # If all fails, return empty dict
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
            'relaxed': ['relaxed', 'chill', 'calm', 'easy'],
            'energetic': ['energetic', 'active', 'dynamic', 'lively'],
            'confident': ['confident', 'bold', 'powerful'],
            'romantic': ['romantic', 'soft', 'elegant']
        }
        for m, words in mood_map.items():
            if any(w in prompt_lower for w in words):
                mood = m
                break
        
        # Detect location
        location = None
        locations = ['beach', 'office', 'gym', 'party', 'home', 'outdoor', 'indoor']
        for loc in locations:
            if loc in prompt_lower:
                location = loc
                break
        
        # Detect occasion
        occasion = None
        occasions = ['party', 'wedding', 'date', 'meeting', 'casual', 'formal', 'business']
        for occ in occasions:
            if occ in prompt_lower:
                occasion = occ
                break
        
        # Detect colors
        colors = []
        color_words = ['blue', 'red', 'green', 'yellow', 'black', 'white', 'gray', 'pink', 
                      'colorful', 'bright', 'dark', 'pastel', 'neutral']
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
        if any(w in prompt_lower for w in ['formal', 'business', 'professional', 'suit']):
            formality = 'formal'
        elif any(w in prompt_lower for w in ['semi-formal', 'smart']):
            formality = 'semi-formal'
        
        logger.info(f"✅ Fallback parse completed")
        
        return ParsedPrompt(
            original_prompt=prompt,
            mood=mood,
            location=location,
            occasion=occasion,
            style=formality,
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
        # Combine important attributes
        query_parts = []
        
        if parsed_prompt.location:
            query_parts.append(parsed_prompt.location)
        if parsed_prompt.occasion:
            query_parts.append(parsed_prompt.occasion)
        if parsed_prompt.style:
            query_parts.append(parsed_prompt.style)
        if parsed_prompt.colors:
            query_parts.extend(parsed_prompt.colors[:2])  # Max 2 colors
        if parsed_prompt.season:
            query_parts.append(parsed_prompt.season)
        
        # Add top keywords
        query_parts.extend(parsed_prompt.keywords[:3])
        
        # Remove duplicates and join
        unique_parts = list(dict.fromkeys(query_parts))
        query = " ".join(unique_parts)
        
        logger.info(f"Generated search query: {query}")
        return query
    
    def health_check(self) -> Dict[str, str]:
        """Check if Llama service is healthy"""
        try:
            # Try a simple inference
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                options={"num_predict": 10}
            )
            return {"status": "healthy", "model": self.model}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
llama_service = LlamaService()


# ==================== TESTING ====================

if __name__ == "__main__":
    # Test the service
    import asyncio
    
    test_prompts = [
        "Beach party, colorful and relaxed",
        "Business meeting, professional and confident",
        "Casual date night, romantic and elegant",
        "Gym workout, comfortable and sporty"
    ]
    
    service = LlamaService()
    
    print("Testing Llama Service...")
    print("=" * 60)
    
    for prompt in test_prompts:
        print(f"\n📝 Prompt: {prompt}")
        print("-" * 60)
        
        parsed = service.parse_outfit_prompt(prompt)
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
    print("Health check:", service.health_check())
