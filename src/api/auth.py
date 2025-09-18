from fastapi import APIRouter, HTTPException, status, Depends
from src.schemas.user import UserSignup, UserLogin, UserResponse
from src.services.auth_service import signup_user, login_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserSignup):
    return signup_user(user)

@router.post("/login", response_model=UserResponse)
def login(user: UserLogin):
    return login_user(user)
