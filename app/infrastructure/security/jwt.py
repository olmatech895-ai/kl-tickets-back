"""JWT token utilities"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.infrastructure.config.settings import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary with data to encode in token (e.g., {"sub": user_id, "username": username})
        expires_delta: Optional expiration time delta. Defaults to 24 hours
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default: 24 hours
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
    except Exception:
        return None


def get_token_expiration_time() -> datetime:
    """Get token expiration time (24 hours from now)"""
    return datetime.utcnow() + timedelta(hours=24)

