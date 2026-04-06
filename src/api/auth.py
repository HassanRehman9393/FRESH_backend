from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import RedirectResponse
from src.schemas.user import UserSignup, UserLogin, UserResponse, GoogleAuthURL, GoogleCallbackData, UserResponseWithAuth
from src.services.auth_service import signup_user, login_user, get_google_auth_url, google_auth_callback
from typing import Optional
from urllib.parse import urlencode
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponseWithAuth, status_code=status.HTTP_201_CREATED)
def signup(user: UserSignup):
    return signup_user(user)

@router.post("/login", response_model=UserResponseWithAuth)
def login(user: UserLogin):
    return login_user(user)


def _resolve_frontend_origin(request: Request, state: Optional[str]) -> str:
    """Resolve safe frontend origin for OAuth callback redirect."""
    candidates = [state, request.headers.get("origin"), "http://localhost:3000"]
    allowed_origins = set(settings.allowed_origins)

    for candidate in candidates:
        if candidate and candidate in allowed_origins:
            return candidate

    return "http://localhost:3000"

@router.get("/google/login", response_model=GoogleAuthURL)
def google_login(request: Request):
    """Get Google OAuth authorization URL."""
    redirect_uri = f"{request.base_url}api/auth/google/callback"
    frontend_origin = _resolve_frontend_origin(request, None)
    auth_url = get_google_auth_url(redirect_uri, frontend_origin)
    return GoogleAuthURL(auth_url=auth_url)

@router.get("/google/callback")
async def google_callback_get(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter")
):
    """Handle Google OAuth callback via GET request (standard OAuth flow)."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    redirect_uri = f"{request.base_url}api/auth/google/callback"
    frontend_origin = _resolve_frontend_origin(request, state)
    user = await google_auth_callback(code, redirect_uri)

    query = urlencode({
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name or "",
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "google_id": user.google_id or "",
        "profile_picture": user.profile_picture or "",
        "access_token": user.access_token,
        "token_type": user.token_type,
    })

    return RedirectResponse(url=f"{frontend_origin}/auth/google/callback?{query}", status_code=302)

@router.post("/google/callback", response_model=UserResponseWithAuth)
async def google_callback_post(request: Request, callback_data: GoogleCallbackData):
    """Handle Google OAuth callback via POST request (alternative flow)."""
    if not callback_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    redirect_uri = f"{request.base_url}api/auth/google/callback"
    return await google_auth_callback(callback_data.code, redirect_uri)
