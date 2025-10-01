from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.user import UserSignup, UserLogin, UserResponse, GoogleAuthURL, GoogleCallbackData, UserResponseWithAuth
from src.services.auth_service import signup_user, login_user, get_google_auth_url, google_auth_callback
from typing import Optional

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponseWithAuth, status_code=status.HTTP_201_CREATED)
def signup(user: UserSignup):
    return signup_user(user)

@router.post("/login", response_model=UserResponseWithAuth)
def login(user: UserLogin):
    return login_user(user)

@router.get("/google/login", response_model=GoogleAuthURL)
def google_login():
    """Get Google OAuth authorization URL."""
    auth_url = get_google_auth_url()
    return GoogleAuthURL(auth_url=auth_url)

@router.get("/google/callback", response_model=UserResponseWithAuth)
async def google_callback_get(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter")
):
    """Handle Google OAuth callback via GET request (standard OAuth flow)."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    return await google_auth_callback(code)

@router.post("/google/callback", response_model=UserResponseWithAuth)
async def google_callback_post(callback_data: GoogleCallbackData):
    """Handle Google OAuth callback via POST request (alternative flow)."""
    if not callback_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    return await google_auth_callback(callback_data.code)
