# 🏗️ AI Outfit Recommender - Technical Flow

## 📋 Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Request Flow](#request-flow)
3. [Component Interactions](#component-interactions)
4. [Data Flow](#data-flow)
5. [Key Technologies](#key-technologies)

---

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  React App (Vite)                                    │  │
│  │  - Firebase Auth (Google OAuth)                     │  │
│  │  - Tinder-style Swipe Interface                     │  │
│  │  - Client-side Image Extraction                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS
                            │
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Railway)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  API Endpoints                                  │  │  │
│  │  │  - /browse-outfits (ASOS/Amazon/Mixed)          │  │  │
│  │  │  - /tryon (Virtual Try-On)                      │  │  │
│  │  │  - /upload/model-image                          │  │  │
│  │  │  - /usage (Rate Limiting)                       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  Services Layer                                  │  │  │
│  │  │  ┌──────────────┐  ┌──────────────┐            │  │  │
│  │  │  │ LLM Service  │  │ Product      │            │  │  │
│  │  │  │ (Groq)       │  │ Service      │            │  │  │
│  │  │  └──────────────┘  └──────────────┘            │  │  │
│  │  │  ┌──────────────┐  ┌──────────────┐            │  │  │
│  │  │  │ ASOS Service │  │ Amazon       │            │  │  │
│  │  │  │ (RapidAPI)   │  │ Service      │            │  │  │
│  │  │  └──────────────┘  └──────────────┘            │  │  │
│  │  │  ┌──────────────┐  ┌──────────────┐            │  │  │
│  │  │  │ Try-On       │  │ Usage        │            │  │  │
│  │  │  │ Service      │  │ Tracker      │            │  │  │
│  │  │  │ (Replicate)  │  │ (SQLite)     │            │  │  │
│  │  │  └──────────────┘  └──────────────┘            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         │              │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │  Groq   │    │ RapidAPI│   │Replicate│   │Cloudinary│
    │   LLM   │    │  ASOS   │   │  IDM-   │   │  Images  │
    │         │    │ Amazon  │   │  VTON   │   │          │
    └─────────┘    └─────────┘   └─────────┘   └─────────┘
```

---

## 🔄 Request Flow

### 1. **User Authentication Flow**

```
User → Frontend → Firebase Auth → Google OAuth
  ↓
Firebase ID Token → Backend → Firebase Admin SDK
  ↓
Verify Token → Extract User ID → Store in Request Context
```

**Key Files:**
- `frontend/src/context/AuthContext.jsx` - Firebase auth
- `backend/app/services/firebase_auth.py` - Token verification
- `backend/app/main.py` - `get_firebase_user()` middleware

---

### 2. **Outfit Search Flow (ASOS/Amazon/Mixed)**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: User Input                                          │
│  User enters: "Beach party, colorful and relaxed"          │
│  Selects: Gender (Men/Women), Store (ASOS/Amazon/Mixed)   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Rate Limiting Check                                 │
│  - Check user's search count (max 1 per user forever)       │
│  - Check global search limit (max 100 total)                │
│  - Increment counters if allowed                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: LLM Prompt Parsing                                  │
│  Service: llm_service.parse_outfit_prompt()                 │
│  API: Groq (Llama 3.3 70B)                                  │
│  Output: {                                                   │
│    mood: "relaxed",                                         │
│    location: "beach",                                       │
│    occasion: "party",                                       │
│    style: "casual",                                         │
│    colors: ["colorful", "bright"],                         │
│    keywords: ["beach", "party", "colorful"]                 │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Product Search (Parallel)                          │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  ASOS Service    │      │  Amazon Service  │           │
│  │  - Search tops   │      │  - Search tops    │           │
│  │  - Search bottoms│      │  - Search bottoms│           │
│  │  - LLM gender    │      │  - LLM gender    │           │
│  │    filtering     │      │    filtering     │           │
│  └──────────────────┘      └──────────────────┘           │
│         │                            │                      │
│         └────────────┬───────────────┘                      │
│                      ▼                                      │
│         RapidAPI → ASOS/Amazon APIs                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: LLM Gender Filtering                                │
│  For each product:                                           │
│  - Analyze name, description, category, brand                │
│  - Classify as Men/Women/Unisex                             │
│  - Filter out wrong gender products                          │
│  - Process in batches of 10 for efficiency                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Outfit Combination Creation                        │
│  Service: product_service.create_outfit_combinations()      │
│                                                              │
│  For each top-bottom pair:                                   │
│  ┌──────────────────────────────────────────────┐         │
│  │  LLM Compatibility Check (NEW!)              │         │
│  │  - Check if top & bottom match stylistically  │         │
│  │  - Analyze: style, color, occasion, aesthetics │         │
│  │  - Return compatibility_score (0.0-1.0)        │         │
│  └──────────────────────────────────────────────┘         │
│                                                              │
│  Match Score Calculation:                                   │
│  - Compatibility: 50% (from LLM)                            │
│  - Price similarity: 30%                                    │
│  - Position bonus: 20%                                      │
│                                                              │
│  Filter: Only keep compatible combinations (score ≥ 0.4)   │
│  Sort: By match_score (descending)                           │
│  Limit: Top 3 combinations                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Response to Frontend                               │
│  {                                                           │
│    success: true,                                            │
│    outfits: [                                                │
│      {                                                       │
│        outfit_id: "uuid",                                   │
│        combination: {                                        │
│          top: { name, price, image_url, buy_url },          │
│          bottom: { name, price, image_url, buy_url },        │
│          total_price: 99.99,                                 │
│          match_score: 0.85                                   │
│        }                                                     │
│      }                                                       │
│    ]                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. **Virtual Try-On Flow**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: User Clicks "Try On"                                │
│  - User swipes right on outfit OR clicks try-on button      │
│  - Frontend extracts product images as Base64               │
│  - Sends: top_image_base64, bottom_image_base64              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Rate Limiting Check                                 │
│  - Check user's try-on count (max 1 per user forever)       │
│  - Check global try-on limit (max 50 total)                  │
│  - Increment if allowed                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Image Processing                                    │
│  - Convert Base64 to PIL Image                              │
│  - Upload to Cloudinary (public URLs)                        │
│  - Get model image (user upload or default)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Virtual Try-On Generation                           │
│  Service: tryon_service.generate_full_outfit_tryon()        │
│                                                              │
│  TWO-PASS Process:                                           │
│  ┌──────────────────────────────────────────────┐         │
│  │  PASS 1: Top on Model                         │         │
│  │  - Replicate API: IDM-VTON model              │         │
│  │  - Input: model_image + top_image              │         │
│  │  - Output: model_with_top.jpg                 │         │
│  └──────────────────────────────────────────────┘         │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────┐         │
│  │  PASS 2: Bottom on Model+Top                  │         │
│  │  - Replicate API: IDM-VTON model               │         │
│  │  - Input: model_with_top + bottom_image       │         │
│  │  - Output: final_outfit_tryon.jpg              │         │
│  └──────────────────────────────────────────────┘         │
│                                                              │
│  Fallback (if AI fails):                                     │
│  - Use rembg for garment extraction                          │
│  - Create simple preview overlay                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Upload Result to Cloudinary                          │
│  - Upload final try-on image                                 │
│  - Get public URL                                            │
│  - Return to frontend                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 Component Interactions

### **Service Dependencies**

```
main.py (FastAPI)
    │
    ├───► llm_service
    │       ├───► Groq API (prompt parsing, gender filtering, compatibility)
    │       └───► Fallback keyword matching
    │
    ├───► asos_service
    │       ├───► RapidAPI ASOS
    │       └───► llm_service (gender filtering)
    │
    ├───► amazon_service
    │       ├───► RapidAPI Amazon
    │       └───► llm_service (gender filtering)
    │
    ├───► product_service
    │       ├───► llm_service (compatibility checking)
    │       └───► Creates OutfitCombination objects
    │
    ├───► tryon_service
    │       ├───► Replicate API (IDM-VTON)
    │       ├───► Cloudinary (image storage)
    │       └───► rembg (fallback extraction)
    │
    ├───► firebase_auth
    │       └───► Firebase Admin SDK
    │
    └───► usage_tracker
            └───► SQLite database
```

---

## 📊 Data Flow

### **Product Data Transformation**

```
RapidAPI Response (ASOS/Amazon)
    │
    ├───► Transform to ProductItem
    │       - id, name, price, currency
    │       - image_url, buy_url
    │       - brand, description, category
    │
    ├───► LLM Gender Filtering
    │       - Filter out wrong gender
    │
    └───► Outfit Combination
            - top + bottom
            - LLM compatibility check
            - match_score calculation
            - Return top 3
```

### **Image Data Flow**

```
Frontend (User Upload)
    │
    ├───► Base64 → Backend
    │       │
    │       ├───► Convert to PIL Image
    │       ├───► Upload to Cloudinary
    │       └───► Store URL in localStorage
    │
Product Images (ASOS/Amazon)
    │
    ├───► Frontend extracts via Canvas API
    │       (Bypasses CORS restrictions)
    │
    ├───► Base64 → Backend
    │       │
    │       ├───► Convert to PIL Image
    │       ├───► Upload to Cloudinary
    │       └───► Use for try-on
    │
Try-On Generation
    │
    ├───► Replicate API (IDM-VTON)
    │       - Two-pass generation
    │       - Returns generated image
    │
    └───► Upload to Cloudinary
            - Get public URL
            - Return to frontend
```

---

## 🛠️ Key Technologies

### **Frontend Stack**
- **React 18** - UI framework
- **Vite** - Build tool
- **Firebase Auth** - Google OAuth
- **Framer Motion** - Animations
- **react-tinder-card** - Swipe interface
- **HTML Canvas API** - Client-side image extraction

### **Backend Stack**
- **FastAPI** - Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **slowapi** - Rate limiting
- **SQLite** - Usage tracking (file-based)

### **AI/ML Services**
- **Groq** - LLM (Llama 3.3 70B)
  - Prompt parsing
  - Gender classification
  - Outfit compatibility checking
- **Replicate** - Virtual Try-On (IDM-VTON)
- **rembg** - Background removal (fallback)

### **External APIs**
- **RapidAPI**
  - ASOS API - Product search
  - Amazon API - Product search
- **Cloudinary** - Image storage & CDN
- **Firebase Admin SDK** - Token verification

### **Infrastructure**
- **Railway** - Backend hosting
- **Vercel** - Frontend hosting
- **Firebase** - Authentication

---

## 🔐 Security & Rate Limiting

### **Rate Limiting Strategy**

```
Per-User Limits (Lifetime):
- 1 search per user (forever)
- 1 try-on per user (forever)

Global Limits (Lifetime):
- 100 total searches (all users)
- 50 total try-ons (all users)

Implementation:
- SQLite database (usage_tracker.py)
- Tracks: user_id, search_count, tryon_count
- Global counters for total usage
- Atomic increments with locks
```

### **Authentication Flow**

```
1. User signs in with Google (Firebase)
2. Frontend receives Firebase ID Token
3. Frontend sends token in Authorization header
4. Backend verifies token with Firebase Admin SDK
5. Extract user_id from token
6. Use user_id for rate limiting & tracking
```

---

## 🚀 Performance Optimizations

1. **Parallel Processing**
   - ASOS & Amazon searches run in parallel
   - Compatibility checks run in batches (10 at a time)
   - Image uploads happen concurrently

2. **Caching**
   - User image stored in localStorage
   - Cloudinary CDN for images

3. **Efficient LLM Usage**
   - Batch processing (10 products at a time)
   - Low temperature (0.1-0.2) for consistency
   - Fallback mechanisms if LLM fails

4. **Image Optimization**
   - Client-side extraction (bypasses server CORS)
   - Cloudinary automatic optimization
   - Base64 encoding for transmission

---

## 📝 Key Design Decisions

1. **No Database for Products**
   - All products fetched real-time from APIs
   - No caching/storage of product data
   - Always fresh inventory

2. **SQLite for Usage Tracking**
   - Simple file-based database
   - No external database needed
   - Sufficient for rate limiting

3. **Client-Side Image Extraction**
   - Solves ASOS image CORS blocking
   - Browser Canvas API extracts images
   - Sends Base64 to backend

4. **Two-Pass Try-On**
   - Better quality than single-pass
   - Top first, then bottom on model+top
   - More realistic results

5. **LLM-Based Filtering**
   - More accurate than keyword matching
   - Understands context and nuance
   - Handles edge cases better

---

## 🔄 Error Handling

1. **LLM Failures**
   - Falls back to keyword matching
   - System continues to work

2. **API Failures**
   - Try-on: Falls back to simple preview
   - Product search: Returns error to user
   - Retry logic with exponential backoff

3. **Rate Limit Exceeded**
   - Clear error messages
   - Shows remaining limits
   - Prevents further requests

---

## 📈 Scalability Considerations

**Current Limitations:**
- SQLite for usage tracking (single file)
- No horizontal scaling
- Global limits are shared across all instances

**Future Improvements:**
- Move to Redis for rate limiting
- Database for usage tracking
- Load balancing for multiple instances
- Caching layer for product searches

---

## 🎯 Summary

**The app follows a clean architecture:**
1. **Frontend** handles UI, auth, and image extraction
2. **Backend** orchestrates services and APIs
3. **LLM** powers intelligent matching and filtering
4. **External APIs** provide products and AI capabilities
5. **Rate limiting** ensures fair usage

**Key Innovation:**
- LLM-based compatibility checking ensures top and bottom actually match
- Client-side image extraction bypasses CORS restrictions
- Two-pass try-on provides better quality results

