-- AI Outfit Recommender Database Schema
-- PostgreSQL with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Products table with vector embeddings
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    price FLOAT NOT NULL,
    currency VARCHAR DEFAULT 'INR',
    
    -- URLs
    image_url VARCHAR NOT NULL,
    buy_url VARCHAR NOT NULL,
    
    -- Details
    brand VARCHAR,
    description TEXT,
    colors JSONB,
    sizes JSONB,
    
    -- Metadata
    style_tags JSONB,
    season VARCHAR,
    occasion VARCHAR,
    
    -- Vector embedding for semantic search (384 dimensions)
    embedding vector(384),
    
    -- Tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Popularity
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    purchase_count INTEGER DEFAULT 0
);

-- Generated outfits table
CREATE TABLE IF NOT EXISTS generated_outfits (
    outfit_id VARCHAR PRIMARY KEY,
    
    -- Product references
    top_id VARCHAR NOT NULL,
    bottom_id VARCHAR NOT NULL,
    
    -- Generated image
    tryon_image_url VARCHAR NOT NULL,
    tryon_image_cloudinary_id VARCHAR,
    
    -- Prompt data
    original_prompt TEXT NOT NULL,
    parsed_prompt JSONB,
    
    -- Metadata
    total_price FLOAT NOT NULL,
    match_score FLOAT,
    style_tags JSONB,
    
    -- Tracking
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    dislike_count INTEGER DEFAULT 0,
    
    -- Performance
    generation_time FLOAT
);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    
    -- References
    outfit_id VARCHAR NOT NULL,
    user_id VARCHAR,
    
    -- Feedback
    action VARCHAR NOT NULL,
    
    -- Metadata
    session_id VARCHAR,
    user_agent VARCHAR,
    ip_address VARCHAR,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Search queries table (analytics)
CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    
    -- Query data
    query TEXT NOT NULL,
    parsed_data JSONB,
    
    -- Results
    results_count INTEGER DEFAULT 0,
    processing_time FLOAT,
    
    -- User tracking
    user_id VARCHAR,
    session_id VARCHAR,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_products_category_price ON products(category, price);

-- Vector similarity search index (IVFFlat for faster searches)
CREATE INDEX IF NOT EXISTS idx_products_embedding 
ON products 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_outfits_top ON generated_outfits(top_id);
CREATE INDEX IF NOT EXISTS idx_outfits_bottom ON generated_outfits(bottom_id);
CREATE INDEX IF NOT EXISTS idx_outfits_generated ON generated_outfits(generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_feedback_outfit ON user_feedback(outfit_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_queries_query ON search_queries(query);
CREATE INDEX IF NOT EXISTS idx_queries_created ON search_queries(created_at DESC);

-- Sample data (optional)
-- INSERT INTO products (id, name, category, price, image_url, buy_url, brand)
-- VALUES ('sample_1', 'Casual T-Shirt', 'top', 599.00, 'https://example.com/tshirt.jpg', 'https://example.com/buy/1', 'Generic');
