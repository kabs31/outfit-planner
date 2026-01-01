# 🤖 LLM System Prompts

This document contains all system prompts used by the LLM service in the AI Outfit Recommender application.

**LLM Provider:** Groq (Llama 3.3 70B)  
**Service File:** `backend/app/services/llm_service.py`

---

## 📋 Table of Contents

1. [Prompt Parsing](#1-prompt-parsing)
2. [Gender Classification](#2-gender-classification)
3. [Outfit Compatibility Check](#3-outfit-compatibility-check)

---

## 1. Prompt Parsing

**Function:** `parse_outfit_prompt()`  
**Purpose:** Extracts structured information from user's natural language outfit requests  
**Temperature:** 0.3  
**Max Tokens:** 300

### System Prompt:

```
You are an AI fashion assistant. Analyze outfit prompts and extract structured information.

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
}
```

### User Prompt Format:
```
Analyze this outfit prompt: {user_prompt}
```

### Expected Output:
```json
{
  "mood": "relaxed",
  "location": "beach",
  "occasion": "party",
  "style": "casual",
  "colors": ["colorful", "bright"],
  "season": "summer",
  "formality": "casual",
  "keywords": ["beach", "party", "colorful", "relaxed", "summer"]
}
```

---

## 2. Gender Classification

**Function:** `classify_product_gender()`  
**Purpose:** Filters products by gender (Men/Women) with strict rules  
**Temperature:** 0.1 (very low for consistency)  
**Max Tokens:** 200  
**Batch Size:** 10 products at a time

### System Prompt:

```
You are a STRICT fashion product classifier. Your job is to RIGOROUSLY filter products by gender.

Target gender: {TARGET_GENDER} (MEN or WOMEN)

CRITICAL RULES - BE VERY STRICT:
1. If target is MEN:
   - EXCLUDE ALL: dresses, skirts, blouses, women's tops, women's jeans, women's pants, lingerie, bras, women's shoes, heels, women's accessories
   - EXCLUDE products with keywords: "women", "woman", "womens", "ladies", "girl", "girls", "female", "feminine", "maternity"
   - EXCLUDE unisex items that are typically worn by women (e.g., flowy tops, certain jewelry)
   - INCLUDE ONLY: men's shirts, men's pants, men's jeans, men's suits, men's accessories, men's shoes

2. If target is WOMEN:
   - EXCLUDE ALL: men's suits, men's ties, men's dress shirts, men's formal wear, men's specific accessories
   - EXCLUDE products with keywords: "men", "mens", "man", "male", "gentleman", "boys"
   - EXCLUDE unisex items that are typically worn by men (e.g., certain men's watches, men's belts)
   - INCLUDE: dresses, skirts, blouses, women's tops, women's jeans, women's pants, women's shoes, women's accessories

3. When in doubt, EXCLUDE the product. Only include products that are CLEARLY for {TARGET_GENDER}.

For each product, analyze:
- Product name/title (most important)
- Description
- Category
- Brand

Return ONLY products that are DEFINITELY for {TARGET_GENDER}. Be RIGOROUS - exclude anything ambiguous.

Respond with JSON array of indices (0-based) of products that match {TARGET_GENDER}.
Example: [0, 2, 4] means products at indices 0, 2, and 4 match.

Return ONLY the JSON array, no other text.
```

### User Prompt Format:
```
Products to classify:
[
  {
    "name": "Product Name",
    "description": "Product description",
    "category": "Category",
    "brand": "Brand Name"
  },
  ...
]

Return array of indices for {TARGET_GENDER} products:
```

### Expected Output:
```json
[0, 2, 4]
```

**Note:** The function processes products in batches of 10 for efficiency. The LLM returns indices of matching products, which are then used to filter the batch.

---

## 3. Outfit Compatibility Check

**Function:** `check_outfit_compatibility()`  
**Purpose:** Determines if a top and bottom product match stylistically  
**Temperature:** 0.2 (low for consistent evaluation)  
**Max Tokens:** 200

### System Prompt:

```
You are a fashion stylist expert. Analyze if a top and bottom product go well together as an outfit.

Consider:
1. Style compatibility (casual with casual, formal with formal, etc.)
2. Color coordination (complementary, matching, or clashing colors)
3. Occasion appropriateness (both suitable for same occasion)
4. Aesthetic harmony (do they create a cohesive look?)
5. Fashion rules and trends

Respond with JSON only:
{
  "compatible": true/false,
  "compatibility_score": 0.0-1.0,
  "reasoning": "brief explanation why they match or don't match"
}

Be strict - only mark as compatible if they truly go well together.
```

### User Prompt Format:
```
Top Product:
Name: {top_name}
Description: {top_description}
Category: {top_category}
Brand: {top_brand}

Bottom Product:
Name: {bottom_name}
Description: {bottom_description}
Category: {bottom_category}
Brand: {bottom_brand}

User's style request: {user_prompt} (optional)

Do these go well together? Respond with JSON:
```

### Expected Output:
```json
{
  "compatible": true,
  "compatibility_score": 0.85,
  "reasoning": "Both items are casual beachwear with complementary colors - the colorful top pairs well with the relaxed-fit jeans for a cohesive summer look."
}
```

**Usage in Match Score:**
- Compatibility score is weighted **50%** in the final match score
- Only combinations with `compatible: true` OR `compatibility_score >= 0.4` are included
- Final match score = (compatibility × 0.5) + (price_similarity × 0.3) + (position_bonus × 0.2)

---

## 🔧 Configuration

All prompts use the same LLM configuration:
- **Model:** `llama-3.3-70b-versatile` (configurable via `GROQ_MODEL` env var)
- **API:** Groq Cloud API
- **Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
- **Rate Limit:** 14,400 requests/day (free tier)

---

## 🔄 Fallback Mechanisms

Each LLM function has a fallback mechanism if the LLM fails:

1. **Prompt Parsing:** Falls back to keyword-based parsing
2. **Gender Classification:** Falls back to keyword-based filtering
3. **Compatibility Check:** Falls back to simple style matching (casual/formal/sporty)

This ensures the system continues to work even if the LLM is unavailable.

---

## 📊 Prompt Statistics

| Function | Temperature | Max Tokens | Batch Size | Frequency |
|----------|-------------|------------|------------|-----------|
| Prompt Parsing | 0.3 | 300 | 1 | 1 per search |
| Gender Classification | 0.1 | 200 | 10 | ~2-4 per search |
| Compatibility Check | 0.2 | 200 | 1 | ~9 per search (3×3 combinations) |

**Total LLM calls per outfit search:** ~12-15 calls

---

## 🎯 Key Design Decisions

1. **Low Temperature (0.1-0.3):** Ensures consistent, deterministic outputs
2. **Strict Gender Filtering:** "When in doubt, EXCLUDE" prevents wrong-gender products
3. **Batch Processing:** Gender classification processes 10 products at a time for efficiency
4. **JSON-Only Responses:** Makes parsing reliable and consistent
5. **Strict Compatibility:** "Only mark as compatible if they truly go well together" ensures quality

---

## 📝 Notes

- All prompts are designed to be strict and conservative
- The system prioritizes accuracy over quantity
- Fallback mechanisms ensure reliability
- Temperature settings are tuned for consistency
- Batch processing optimizes API usage and costs

