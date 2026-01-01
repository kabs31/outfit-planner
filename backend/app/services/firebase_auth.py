"""
Firebase Authentication Service
Verifies Firebase ID tokens for authenticated requests
"""

import logging
from typing import Optional
import httpx
from jose import jwt, JWTError
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Firebase public keys URL
FIREBASE_KEYS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
FIREBASE_PROJECT_ID = "outfit-planner-ca620"

# Cache for Firebase public keys
_cached_keys = None
_keys_expiry = None


async def get_firebase_public_keys():
    """Fetch Firebase public keys (cached)"""
    global _cached_keys, _keys_expiry
    
    now = datetime.utcnow()
    
    # Return cached keys if still valid
    if _cached_keys and _keys_expiry and now < _keys_expiry:
        return _cached_keys
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(FIREBASE_KEYS_URL)
            
            if response.status_code == 200:
                _cached_keys = response.json()
                
                # Parse cache-control header for expiry
                cache_control = response.headers.get("cache-control", "")
                max_age = 3600  # Default 1 hour
                for part in cache_control.split(","):
                    if "max-age=" in part:
                        try:
                            max_age = int(part.split("=")[1].strip())
                        except:
                            pass
                
                from datetime import timedelta
                _keys_expiry = now + timedelta(seconds=max_age)
                
                return _cached_keys
    except Exception as e:
        logger.error(f"Failed to fetch Firebase keys: {e}")
    
    return _cached_keys  # Return cached even if expired, as fallback


async def verify_firebase_token(token: str) -> Optional[dict]:
    """
    Verify a Firebase ID token
    Returns the decoded token payload if valid, None otherwise
    """
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            logger.warning("Token missing kid header")
            return None
        
        # Get public keys
        keys = await get_firebase_public_keys()
        if not keys or kid not in keys:
            logger.warning(f"Key {kid} not found in Firebase keys")
            return None
        
        # Get the public key
        public_key = keys[kid]
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
        )
        
        # Verify expiration
        exp = payload.get("exp", 0)
        if datetime.utcnow().timestamp() > exp:
            logger.warning("Token expired")
            return None
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def get_user_id_from_token(payload: dict) -> str:
    """Extract user ID from decoded token"""
    return payload.get("user_id") or payload.get("sub")


def get_user_email_from_token(payload: dict) -> Optional[str]:
    """Extract email from decoded token"""
    return payload.get("email")


