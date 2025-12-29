"""
Database setup and models for AI Outfit App
SQLAlchemy models with pgvector for embeddings
"""
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, JSON, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ==================== DATABASE MODELS ====================

class Product(Base):
    """Product table with vector embeddings for semantic search"""
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # top, bottom, dress, etc.
    price = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    
    # URLs
    image_url = Column(String, nullable=False)
    buy_url = Column(String, nullable=False)
    
    # Product details
    brand = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    colors = Column(JSON, nullable=True)  # ["blue", "white"]
    sizes = Column(JSON, nullable=True)   # ["S", "M", "L"]
    
    # Metadata
    style_tags = Column(JSON, nullable=True)  # ["casual", "beach", "summer"]
    season = Column(String, nullable=True)     # "summer", "winter", etc.
    occasion = Column(String, nullable=True)   # "party", "formal", etc.
    
    # Vector embedding for semantic search (384 dimensions for MiniLM)
    embedding = Column(Vector(384), nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Popularity/ranking
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)


class GeneratedOutfit(Base):
    """Generated outfit combinations with try-on images"""
    __tablename__ = "generated_outfits"
    
    outfit_id = Column(String, primary_key=True, index=True)
    
    # Product references
    top_id = Column(String, nullable=False, index=True)
    bottom_id = Column(String, nullable=False, index=True)
    
    # Generated image
    tryon_image_url = Column(String, nullable=False)
    tryon_image_cloudinary_id = Column(String, nullable=True)
    
    # User prompt and parsed data
    original_prompt = Column(Text, nullable=False)
    parsed_prompt = Column(JSON, nullable=True)  # Structured prompt data
    
    # Metadata
    total_price = Column(Float, nullable=False)
    match_score = Column(Float, nullable=True)  # 0-1 score of how well items match
    style_tags = Column(JSON, nullable=True)
    
    # Tracking
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    
    # Performance
    generation_time = Column(Float, nullable=True)  # Seconds taken to generate


class UserFeedback(Base):
    """User feedback on generated outfits"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # References
    outfit_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # Optional user tracking
    
    # Feedback
    action = Column(String, nullable=False)  # like, dislike, skip
    
    # Metadata
    session_id = Column(String, nullable=True)  # Track user sessions
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchQuery(Base):
    """Track user search queries for analytics"""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query data
    query = Column(Text, nullable=False, index=True)
    parsed_data = Column(JSON, nullable=True)
    
    # Results
    results_count = Column(Integer, default=0)
    processing_time = Column(Float, nullable=True)
    
    # User tracking
    user_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== DATABASE FUNCTIONS ====================

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        # Enable pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def create_indexes():
    """Create additional indexes for performance"""
    try:
        with engine.connect() as conn:
            # Create IVFFlat index on embedding column for faster similarity search
            # This is for when you have many products (1000+)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS products_embedding_idx 
                ON products 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            # Additional indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_category_price 
                ON products (category, price);
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_active 
                ON products (is_active) 
                WHERE is_active = true;
            """)
            
            conn.commit()
            logger.info("✅ Database indexes created successfully")
            
    except Exception as e:
        logger.warning(f"⚠️  Failed to create indexes (may already exist): {e}")


# ==================== HELPER FUNCTIONS ====================

def check_db_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_product_count():
    """Get total number of products in database"""
    try:
        with SessionLocal() as db:
            return db.query(Product).filter(Product.is_active == True).count()
    except Exception as e:
        logger.error(f"❌ Failed to get product count: {e}")
        return 0


def get_outfit_count():
    """Get total number of generated outfits"""
    try:
        with SessionLocal() as db:
            return db.query(GeneratedOutfit).count()
    except Exception as e:
        logger.error(f"❌ Failed to get outfit count: {e}")
        return 0


# ==================== SEED DATA (For Development) ====================

def seed_sample_products():
    """Add sample products for testing (uses FakeStoreAPI data)"""
    sample_products = [
        {
            "id": "sample_top_1",
            "name": "Casual Cotton T-Shirt",
            "category": "top",
            "price": 599.00,
            "image_url": "https://fakestoreapi.com/img/71-3HjGNDUL._AC_SY879._SX._UX._SY._UY_.jpg",
            "buy_url": "https://fakestoreapi.com/products/1",
            "brand": "Generic",
            "colors": ["white", "blue"],
            "sizes": ["S", "M", "L", "XL"],
            "style_tags": ["casual", "everyday", "comfortable"],
            "season": "all",
            "occasion": "casual"
        },
        {
            "id": "sample_bottom_1",
            "name": "Slim Fit Jeans",
            "category": "bottom",
            "price": 1299.00,
            "image_url": "https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",
            "buy_url": "https://fakestoreapi.com/products/2",
            "brand": "Generic",
            "colors": ["blue", "black"],
            "sizes": ["28", "30", "32", "34"],
            "style_tags": ["casual", "denim", "everyday"],
            "season": "all",
            "occasion": "casual"
        }
    ]
    
    try:
        with SessionLocal() as db:
            for prod_data in sample_products:
                # Check if already exists
                existing = db.query(Product).filter(Product.id == prod_data["id"]).first()
                if not existing:
                    product = Product(**prod_data)
                    db.add(product)
            
            db.commit()
            logger.info(f"✅ Seeded {len(sample_products)} sample products")
            
    except Exception as e:
        logger.error(f"❌ Failed to seed products: {e}")


if __name__ == "__main__":
    # For testing database setup
    print("Initializing database...")
    init_db()
    create_indexes()
    print(f"Products in database: {get_product_count()}")
    print(f"Outfits generated: {get_outfit_count()}")
