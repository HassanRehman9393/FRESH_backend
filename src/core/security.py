from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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
