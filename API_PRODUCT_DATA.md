# 📦 API Product Data Structure

This document details what product information is received from ASOS and Amazon APIs, and how it's transformed for use in the application.

---

## 📋 Table of Contents

1. [ASOS API Response](#asos-api-response)
2. [Amazon API Response](#amazon-api-response)
3. [Transformed Product Format](#transformed-product-format)
4. [Field Mapping](#field-mapping)

---

## 🛍️ ASOS API Response

**API Endpoint:** `https://asos10.p.rapidapi.com/api/v1/getProductListBySearchTerm`  
**Service File:** `backend/app/services/asos_service.py`

### Raw API Response Structure

The ASOS API returns products in the following structure:

```json
{
  "data": {
    "products": [
      {
        "id": "12345678",
        "name": "ASOS DESIGN relaxed t-shirt in white",
        "price": {
          "current": {
            "value": 19.99,
            "text": "$19.99"
          },
          "previous": {
            "value": 24.99,
            "text": "$24.99"
          },
          "currency": "USD"
        },
        "imageUrl": "https://images.asos-media.com/products/asos-design-relaxed-t-shirt-in-white/12345678-1-white",
        "image": "https://images.asos-media.com/products/asos-design-relaxed-t-shirt-in-white/12345678-1-white",
        "url": "/prd/12345678",
        "brandName": "ASOS DESIGN",
        "colour": "White",
        "isAvailable": true,
        "isNoSize": false,
        "isOneSize": false,
        "variants": [],
        "sizes": [],
        "description": "Relaxed fit t-shirt in white cotton",
        "category": "Tops",
        "gender": "Women"
      }
    ]
  }
}
```

### Fields Extracted from ASOS API

| Field | Source | Description | Example |
|-------|--------|-------------|---------|
| `id` | `product.id` | Unique product identifier | `"12345678"` |
| `name` | `product.name` | Product name/title | `"ASOS DESIGN relaxed t-shirt"` |
| `price` | `product.price.current.value` | Current price in USD | `19.99` |
| `image_url` | `product.imageUrl` or `product.image` | Product image URL | `"https://images.asos-media.com/..."` |
| `product_url` | `product.url` | Product page URL (relative) | `"/prd/12345678"` |
| `brand` | `product.brandName` | Brand name | `"ASOS DESIGN"` |
| `color` | `product.colour` | Product color | `"White"` |
| `description` | `product.description` | Product description | `"Relaxed fit t-shirt..."` |
| `category` | `product.category` | Product category | `"Tops"` |
| `gender` | `product.gender` | Gender (if available) | `"Women"` |

### ASOS-Specific Processing

1. **Price Conversion:** USD → INR (multiplied by 83.0)
2. **Image URL:** Ensures `https://` prefix if missing
3. **Product URL:** Converts relative URL to full URL: `https://www.asos.com/in{url}`
4. **Currency:** Always converted to INR for display

---

## 🛒 Amazon API Response

**API Endpoint:** `https://real-time-amazon-data.p.rapidapi.com/search`  
**Service File:** `backend/app/services/amazon_service.py`

### Raw API Response Structure

The Amazon API returns products in the following structure:

```json
{
  "data": {
    "products": [
      {
        "asin": "B08XYZ1234",
        "product_title": "Men's Casual T-Shirt - Cotton Comfort Fit",
        "product_price": "₹1,299.00",
        "product_photo": "https://m.media-amazon.com/images/I/71abc123.jpg",
        "product_main_image_url": "https://m.media-amazon.com/images/I/71abc123.jpg",
        "product_url": "https://www.amazon.in/dp/B08XYZ1234",
        "product_brand": "Generic",
        "product_star_rating": "4.3 out of 5 stars",
        "product_num_ratings": 1234,
        "rank": 1,
        "is_best_seller": true,
        "is_prime": true,
        "availability": "In Stock",
        "category": "Clothing & Accessories",
        "description": "Comfortable cotton t-shirt for everyday wear"
      }
    ]
  }
}
```

### Fields Extracted from Amazon API

| Field | Source | Description | Example |
|-------|--------|-------------|---------|
| `asin` | `product.asin` | Amazon Standard Identification Number | `"B08XYZ1234"` |
| `name` | `product.product_title` or `product.title` | Product title | `"Men's Casual T-Shirt"` |
| `price` | `product.product_price` | Price string (parsed) | `"₹1,299.00"` → `1299.0` |
| `image_url` | `product.product_photo` or `product.product_main_image_url` | Product image URL | `"https://m.media-amazon.com/..."` |
| `product_url` | `product.product_url` | Product page URL | `"https://www.amazon.in/dp/..."` |
| `brand` | `product.product_brand` | Brand name | `"Generic"` |
| `rating` | `product.product_star_rating` | Star rating | `"4.3 out of 5 stars"` |
| `reviews` | `product.product_num_ratings` | Number of reviews | `1234` |
| `rank` | `product.rank` | Best seller rank | `1` |
| `description` | `product.description` | Product description | `"Comfortable cotton..."` |
| `category` | `product.category` | Product category | `"Clothing & Accessories"` |

### Amazon-Specific Processing

1. **Price Parsing:** Extracts numeric value from price string (handles `₹1,299.00`, `$29.99`, etc.)
2. **Image URL:** Uses `product_photo` first, falls back to `product_main_image_url`
3. **Product URL:** Uses provided URL or constructs from ASIN: `https://www.amazon.in/dp/{asin}`
4. **Name Truncation:** Limits product name to 100 characters
5. **Currency:** Always INR (India store)

---

## 🔄 Transformed Product Format

Both APIs transform their responses to a unified format used throughout the application:

```json
{
  "id": "12345678",
  "name": "ASOS DESIGN relaxed t-shirt in white",
  "category": "top",
  "price": 1659.17,
  "currency": "INR",
  "image_url": "https://images.asos-media.com/products/...",
  "buy_url": "https://www.asos.com/in/prd/12345678",
  "brand": "ASOS DESIGN",
  "description": "ASOS DESIGN relaxed t-shirt in white",
  "colors": ["White"],
  "sizes": [],
  "source": "asos"
}
```

### Standard Fields (All Products)

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | string | Unique product identifier | ✅ Yes |
| `name` | string | Product name/title | ✅ Yes |
| `category` | string | Product category (`top`, `bottom`, `dress`) | ✅ Yes |
| `price` | float | Price in INR | ✅ Yes |
| `currency` | string | Currency code (always `"INR"`) | ✅ Yes |
| `image_url` | string | Product image URL | ✅ Yes |
| `buy_url` | string | Product purchase URL | ✅ Yes |
| `brand` | string | Brand name | ✅ Yes |
| `description` | string | Product description | ⚠️ Optional |
| `colors` | array | List of colors | ⚠️ Optional |
| `sizes` | array | Available sizes | ⚠️ Optional |
| `source` | string | Source store (`"asos"` or `"amazon"`) | ✅ Yes |

### Amazon-Specific Additional Fields

| Field | Type | Description |
|-------|------|-------------|
| `rating` | string | Star rating (e.g., `"4.3 out of 5 stars"`) |
| `reviews` | number | Number of reviews |
| `best_seller_rank` | number | Best seller rank |

---

## 📊 Field Mapping

### ASOS → Transformed Format

```python
{
    "id": str(product.get("id", "")),
    "name": product.get("name", "Fashion Item"),
    "category": category,  # "top", "bottom", "dress"
    "price": round(price * 83.0, 2),  # USD → INR
    "currency": "INR",
    "image_url": image_url,  # With https:// prefix
    "buy_url": f"https://www.asos.com/in{product_url}",
    "brand": product.get("brandName", "ASOS"),
    "description": name,  # Uses name as description
    "colors": [color] if color else [],
    "sizes": [],
    "source": "asos"
}
```

### Amazon → Transformed Format

```python
{
    "id": product.get("asin", ""),
    "name": name[:100],  # Truncated to 100 chars
    "category": category,  # "top", "bottom"
    "price": parsed_price,  # Extracted from price string
    "currency": "INR",
    "image_url": image_url,
    "buy_url": product_url or f"https://www.amazon.in/dp/{asin}",
    "brand": product.get("product_brand", "Amazon"),
    "description": name,  # Uses name as description
    "colors": [],
    "sizes": [],
    "source": "amazon",
    "rating": rating,  # Optional
    "reviews": reviews,  # Optional
    "best_seller_rank": rank  # Optional
}
```

---

## 🔍 Data Quality & Validation

### Required Fields Check

Both services skip products that don't have:
- ✅ Valid `id`
- ✅ Valid `name`
- ✅ Valid `image_url` (required for display)
- ✅ Valid `price` (> 0)

### Missing Data Handling

| Field | Default Value | Notes |
|-------|---------------|-------|
| `name` | `"Fashion Item"` | Fallback if missing |
| `brand` | `"ASOS"` or `"Amazon"` | Store name as fallback |
| `description` | Same as `name` | Uses name if description missing |
| `colors` | `[]` | Empty array if no color info |
| `sizes` | `[]` | Empty array (not used currently) |
| `price` | `0.0` | Skipped if price is 0 |

---

## 🎯 Usage in Application

### After Transformation

1. **LLM Gender Filtering:** Products are filtered by gender using LLM
2. **Outfit Combination:** Products are combined into outfits
3. **LLM Compatibility Check:** Top-bottom pairs are checked for style compatibility
4. **Frontend Display:** Transformed format is sent to frontend

### ProductItem Model

The transformed data is converted to `ProductItem` Pydantic model:

```python
class ProductItem(BaseModel):
    id: str
    name: str
    category: str
    price: float
    currency: str
    image_url: str
    buy_url: str
    brand: Optional[str] = None
    description: Optional[str] = None
```

---

## 📝 Notes

1. **ASOS Price Conversion:** Always converts USD to INR (rate: 83.0)
2. **Amazon Price Parsing:** Handles various price formats with regex
3. **Image URLs:** Both APIs provide direct image URLs (no extraction needed)
4. **Product URLs:** Both provide direct purchase links
5. **Brand Information:** ASOS has better brand data; Amazon often shows "Generic"
6. **Color Information:** Only ASOS provides color data; Amazon doesn't
7. **Rating/Reviews:** Only Amazon provides rating and review data

---

## 🔄 API Response Examples

### ASOS API Response (Raw)

```json
{
  "data": {
    "products": [
      {
        "id": "12345678",
        "name": "ASOS DESIGN relaxed t-shirt in white",
        "price": {
          "current": {
            "value": 19.99,
            "text": "$19.99"
          }
        },
        "imageUrl": "https://images.asos-media.com/products/...",
        "url": "/prd/12345678",
        "brandName": "ASOS DESIGN",
        "colour": "White"
      }
    ]
  }
}
```

### Amazon API Response (Raw)

```json
{
  "data": {
    "products": [
      {
        "asin": "B08XYZ1234",
        "product_title": "Men's Casual T-Shirt",
        "product_price": "₹1,299.00",
        "product_photo": "https://m.media-amazon.com/images/I/...",
        "product_url": "https://www.amazon.in/dp/B08XYZ1234",
        "product_brand": "Generic",
        "product_star_rating": "4.3 out of 5 stars",
        "product_num_ratings": 1234
      }
    ]
  }
}
```

### Final Transformed Format (Both)

```json
{
  "id": "12345678",
  "name": "ASOS DESIGN relaxed t-shirt in white",
  "category": "top",
  "price": 1659.17,
  "currency": "INR",
  "image_url": "https://images.asos-media.com/products/...",
  "buy_url": "https://www.asos.com/in/prd/12345678",
  "brand": "ASOS DESIGN",
  "description": "ASOS DESIGN relaxed t-shirt in white",
  "colors": ["White"],
  "sizes": [],
  "source": "asos"
}
```

