from src.schemas.user import UserSignup, UserLogin, UserResponse, UserRole
from src.core.supabase_client import supabase
from fastapi import HTTPException, status
from src.core.security import hash_password, verify_password
import uuid

def signup_user(user: UserSignup) -> UserResponse:
    # Check if user exists
    existing = supabase.table("users").select("id").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    # Hash password
    password_hash = hash_password(user.password)
    # Create user
    result = supabase.table("users").insert({
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password_hash": password_hash,
        "full_name": user.full_name,
        "role": user.role.value
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed.")
    user_data = result.data[0]
    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        role=UserRole(user_data["role"])
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
