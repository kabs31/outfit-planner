"""
Usage Tracking Service
- Per-user: 1 search + 1 try-on (lifetime, never resets)
- Global: Limited total searches/try-ons across all users
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# ============ LIMITS (CHANGE THESE) ============
# Per-user limits (lifetime - never resets)
USER_SEARCH_LIMIT = 1   # Each user gets 1 search ever
USER_TRYON_LIMIT = 1    # Each user gets 1 try-on ever

# Global limits (across ALL users)
GLOBAL_SEARCH_LIMIT = 100   # Total searches allowed (all users combined)
GLOBAL_TRYON_LIMIT = 50     # Total try-ons allowed (all users combined)
# ===============================================

# Database file
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "usage.db")


def _get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_usage_db():
    """Initialize the usage database"""
    conn = _get_connection()
    try:
        # Per-user usage table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_usage (
                user_id TEXT PRIMARY KEY,
                search_count INTEGER DEFAULT 0,
                tryon_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Global usage table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_usage (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_searches INTEGER DEFAULT 0,
                total_tryons INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize global counter if not exists
        conn.execute("""
            INSERT OR IGNORE INTO global_usage (id, total_searches, total_tryons)
            VALUES (1, 0, 0)
        """)
        
        conn.commit()
        logger.info("✅ Usage database initialized")
    except Exception as e:
        logger.error(f"Failed to init usage db: {e}")
    finally:
        conn.close()


# Initialize on module load
init_usage_db()


def get_global_usage() -> Dict:
    """Get global usage stats"""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM global_usage WHERE id = 1").fetchone()
        if row:
            total_searches = row["total_searches"]
            total_tryons = row["total_tryons"]
            return {
                "total_searches": total_searches,
                "total_tryons": total_tryons,
                "searches_remaining": max(0, GLOBAL_SEARCH_LIMIT - total_searches),
                "tryons_remaining": max(0, GLOBAL_TRYON_LIMIT - total_tryons),
                "global_search_limit": GLOBAL_SEARCH_LIMIT,
                "global_tryon_limit": GLOBAL_TRYON_LIMIT,
                "searches_available": total_searches < GLOBAL_SEARCH_LIMIT,
                "tryons_available": total_tryons < GLOBAL_TRYON_LIMIT,
            }
        return {
            "total_searches": 0,
            "total_tryons": 0,
            "searches_remaining": GLOBAL_SEARCH_LIMIT,
            "tryons_remaining": GLOBAL_TRYON_LIMIT,
            "searches_available": True,
            "tryons_available": True,
        }
    finally:
        conn.close()


def get_user_usage(user_id: str) -> Dict:
    """Get usage for a specific user"""
    conn = _get_connection()
    try:
        # Get user's usage
        row = conn.execute(
            "SELECT * FROM user_usage WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if row:
            search_count = row["search_count"]
            tryon_count = row["tryon_count"]
        else:
            search_count = 0
            tryon_count = 0
        
        # Get global usage
        global_usage = get_global_usage()
        
        # User can search if: they haven't used their 1 search AND global limit not reached
        can_search = (search_count < USER_SEARCH_LIMIT) and global_usage["searches_available"]
        
        # User can try-on if: they haven't used their 1 try-on AND global limit not reached
        can_tryon = (tryon_count < USER_TRYON_LIMIT) and global_usage["tryons_available"]
        
        return {
            # User limits
            "search_count": search_count,
            "tryon_count": tryon_count,
            "search_limit": USER_SEARCH_LIMIT,
            "tryon_limit": USER_TRYON_LIMIT,
            "can_search": can_search,
            "can_tryon": can_tryon,
            "search_exhausted": search_count >= USER_SEARCH_LIMIT,
            "tryon_exhausted": tryon_count >= USER_TRYON_LIMIT,
            
            # Global limits
            "global_searches_remaining": global_usage["searches_remaining"],
            "global_tryons_remaining": global_usage["tryons_remaining"],
            
            # Legacy compatibility
            "browse_count": search_count,
            "browse_limit": USER_SEARCH_LIMIT,
            "can_browse": can_search,
        }
        
    finally:
        conn.close()


def increment_search(user_id: str) -> bool:
    """
    Increment search count for user.
    Returns True if successful, False if limit reached.
    """
    conn = _get_connection()
    try:
        # Check global limit first
        global_usage = get_global_usage()
        if not global_usage["searches_available"]:
            logger.warning(f"Global search limit reached!")
            return False
        
        # Check user limit
        user_usage = get_user_usage(user_id)
        if user_usage["search_exhausted"]:
            logger.warning(f"User {user_id[:8]}... already used their search")
            return False
        
        # Increment user count
        conn.execute("""
            INSERT INTO user_usage (user_id, search_count, tryon_count)
            VALUES (?, 1, 0)
            ON CONFLICT(user_id) DO UPDATE SET search_count = search_count + 1
        """, (user_id,))
        
        # Increment global count
        conn.execute("""
            UPDATE global_usage 
            SET total_searches = total_searches + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """)
        
        conn.commit()
        logger.info(f"✅ Search used by {user_id[:8]}... (Global: {global_usage['total_searches'] + 1}/{GLOBAL_SEARCH_LIMIT})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to increment search: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def increment_tryon(user_id: str) -> bool:
    """
    Increment try-on count for user.
    Returns True if successful, False if limit reached.
    """
    conn = _get_connection()
    try:
        # Check global limit first
        global_usage = get_global_usage()
        if not global_usage["tryons_available"]:
            logger.warning(f"Global try-on limit reached!")
            return False
        
        # Check user limit
        user_usage = get_user_usage(user_id)
        if user_usage["tryon_exhausted"]:
            logger.warning(f"User {user_id[:8]}... already used their try-on")
            return False
        
        # Increment user count
        conn.execute("""
            INSERT INTO user_usage (user_id, search_count, tryon_count)
            VALUES (?, 0, 1)
            ON CONFLICT(user_id) DO UPDATE SET tryon_count = tryon_count + 1
        """, (user_id,))
        
        # Increment global count
        conn.execute("""
            UPDATE global_usage 
            SET total_tryons = total_tryons + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """)
        
        conn.commit()
        logger.info(f"✅ Try-on used by {user_id[:8]}... (Global: {global_usage['total_tryons'] + 1}/{GLOBAL_TRYON_LIMIT})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to increment try-on: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# Legacy function names for compatibility
def increment_browse(user_id: str) -> bool:
    """Legacy: Use increment_search instead"""
    return increment_search(user_id)


def get_admin_stats() -> Dict:
    """Get admin statistics (for monitoring)"""
    conn = _get_connection()
    try:
        # Count total users
        user_count = conn.execute("SELECT COUNT(*) FROM user_usage").fetchone()[0]
        
        # Get global usage
        global_usage = get_global_usage()
        
        return {
            "total_users": user_count,
            "total_searches_used": global_usage["total_searches"],
            "total_tryons_used": global_usage["total_tryons"],
            "searches_remaining": global_usage["searches_remaining"],
            "tryons_remaining": global_usage["tryons_remaining"],
            "global_search_limit": GLOBAL_SEARCH_LIMIT,
            "global_tryon_limit": GLOBAL_TRYON_LIMIT,
        }
    finally:
        conn.close()
