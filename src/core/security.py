from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.core.config import settings
import bcrypt
import logging

logger = logging.getLogger(__name__)

# Bcrypt configuration
BCRYPT_ROUNDS = 12
MAX_PASSWORD_LENGTH = 72  # bcrypt limitation in bytes

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt directly (bypassing passlib to avoid version detection issues).
    Bcrypt has a 72-byte limit, so we truncate if necessary.
    """
    try:
        # Encode password and truncate to 72 bytes if necessary
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > MAX_PASSWORD_LENGTH:
            logger.warning(f"Password exceeds {MAX_PASSWORD_LENGTH} bytes, truncating")
            password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise Exception(f"Password hashing failed: {str(e)}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password using bcrypt directly (bypassing passlib to avoid version detection issues).
    Bcrypt has a 72-byte limit, so we truncate if necessary.
    """
    try:
        # Encode password and truncate to 72 bytes if necessary
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > MAX_PASSWORD_LENGTH:
            logger.warning(f"Password exceeds {MAX_PASSWORD_LENGTH} bytes, truncating")
            password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
        
        # Encode hashed password if it's a string
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
        
        # Verify password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        # Map 'sub' to 'user_id' for consistency
        if 'sub' in payload:
            payload['user_id'] = payload['sub']
        return payload
    except JWTError:
        return None

def create_user_token(user_id: str, email: str, role: str) -> str:
    """Create access token with user information."""
    token_data = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access"
    }
    return create_access_token(token_data)
