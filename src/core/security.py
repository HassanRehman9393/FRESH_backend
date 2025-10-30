from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.core.config import settings
import bcrypt

# Configure passlib with fallback options
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12,  # Set explicit rounds
)

def hash_password(password: str) -> str:
    """Hash password with bcrypt, handling length limitations."""
    try:
        # Ensure password is not longer than 72 bytes (bcrypt limitation)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Error hashing password: {e}")
        # Fallback to direct bcrypt if passlib fails
        try:
            import bcrypt
            password_bytes = password.encode('utf-8')[:72]  # Limit to 72 bytes
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        except Exception as fallback_error:
            print(f"Fallback bcrypt also failed: {fallback_error}")
            raise Exception(f"Password hashing failed: {str(e)}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password with bcrypt, handling length limitations."""
    try:
        # Ensure password is not longer than 72 bytes (bcrypt limitation)
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        # Fallback to direct bcrypt if passlib fails
        try:
            import bcrypt
            password_bytes = plain_password.encode('utf-8')[:72]  # Limit to 72 bytes
            hashed_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as fallback_error:
            print(f"Fallback bcrypt verification also failed: {fallback_error}")
            return False  # Return False instead of raising exception for verification

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
