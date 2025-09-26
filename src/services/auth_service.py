from src.schemas.user import UserSignup, UserLogin, UserResponse, UserRole, GoogleUserData, UserResponseWithAuth
from src.core.supabase_client import supabase
from fastapi import HTTPException, status
from src.core.security import hash_password, verify_password, create_user_token
from src.core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from authlib.integrations.starlette_client import OAuth
import uuid
import httpx
from typing import Dict, Any

# Initialize OAuth client
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def signup_user(user: UserSignup) -> UserResponseWithAuth:
    # Check if user exists
    existing = supabase.table("users").select("id").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    
    # For regular signup, password is required
    if not user.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required for regular signup.")
    
    # Hash password
    password_hash = hash_password(user.password)
    # Create user
    user_data = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password_hash": password_hash,
        "full_name": user.full_name,
        "role": user.role.value,
        "provider": "local",
        "is_google_user": False
    }
    
    result = supabase.table("users").insert(user_data).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed.")
    
    created_user = result.data[0]
    
    # Create JWT token
    access_token = create_user_token(
        created_user["id"],
        created_user["email"],
        created_user["role"]
    )
    
    return UserResponseWithAuth(
        id=created_user["id"],
        email=created_user["email"],
        full_name=created_user.get("full_name"),
        role=UserRole(created_user["role"]),
        access_token=access_token,
        token_type="bearer"
    )

def login_user(user: UserLogin) -> UserResponseWithAuth:
    result = supabase.table("users").select("*").eq("email", user.email).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    user_data = result.data[0]
    
    # Check if user is Google user trying to login with password
    if user_data.get("is_google_user") or user_data.get("provider") == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="This account uses Google login. Please use Google sign-in."
        )
    
    if not user_data.get("password_hash") or not verify_password(user.password, user_data["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    # Create JWT token
    access_token = create_user_token(
        user_data["id"],
        user_data["email"],
        user_data["role"]
    )
    
    return UserResponseWithAuth(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        role=UserRole(user_data["role"]),
        google_id=user_data.get("google_id"),
        profile_picture=user_data.get("profile_picture"),
        access_token=access_token,
        token_type="bearer"
    )

def login_user(user: UserLogin) -> UserResponse:
    result = supabase.table("users").select("id", "email", "full_name", "role", "password_hash").eq("email", user.email).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    user_data = result.data[0]
    if not verify_password(user.password, user_data["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        role=UserRole(user_data["role"])
    )

def get_google_auth_url() -> str:
    """Generate Google OAuth authorization URL."""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={settings.google_redirect_uri}&"
        f"scope=openid email profile&"
        f"response_type=code&"
        f"access_type=offline"
    )
    return google_auth_url

async def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google ID token and return user info."""
    try:
        # Verify the token with clock skew tolerance
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.google_client_id,
            clock_skew_in_seconds=10  # Allow 10 seconds of clock skew
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return idinfo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

async def exchange_code_for_token(code: str) -> str:
    """Exchange authorization code for access token."""
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
            
        token_data = response.json()
        return token_data.get("id_token")

async def google_auth_callback(code: str) -> UserResponseWithAuth:
    """Handle Google OAuth callback and login/signup user."""
    try:
        # Exchange code for token
        id_token_str = await exchange_code_for_token(code)
        
        # Verify token and get user info
        user_info = await verify_google_token(id_token_str)
        
        google_id = user_info.get("sub")
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        profile_picture = user_info.get("picture")
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required user information from Google"
            )
        
        # Check if user exists by Google ID
        existing_user = supabase.table("users").select("*").eq("google_id", google_id).execute()
        
        if existing_user.data:
            # User exists, login
            user_data = existing_user.data[0]
        else:
            # Check if user exists by email (might be existing local user)
            email_user = supabase.table("users").select("*").eq("email", email).execute()
            
            if email_user.data:
                # Update existing user with Google info
                user_data = email_user.data[0]
                update_result = supabase.table("users").update({
                    "google_id": google_id,
                    "profile_picture": profile_picture,
                    "is_google_user": True,
                    "provider": "google",
                    "full_name": full_name or user_data.get("full_name")
                }).eq("id", user_data["id"]).execute()
                
                if update_result.data:
                    user_data = update_result.data[0]
            else:
                # Create new user
                new_user = {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "full_name": full_name,
                    "google_id": google_id,
                    "profile_picture": profile_picture,
                    "is_google_user": True,
                    "provider": "google",
                    "role": UserRole.farmer.value,
                    "password_hash": None  # No password for Google users
                }
                
                result = supabase.table("users").insert(new_user).execute()
                if not result.data:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user"
                    )
                user_data = result.data[0]
        
        # Create JWT token
        access_token = create_user_token(
            user_data["id"], 
            user_data["email"], 
            user_data["role"]
        )
        
        return UserResponseWithAuth(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            role=UserRole(user_data["role"]),
            google_id=user_data.get("google_id"),
            profile_picture=user_data.get("profile_picture"),
            access_token=access_token,
            token_type="bearer"
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )
