from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    farmer = "farmer"
    exporter = "exporter"
    government = "government"
    admin = "admin"

class UserSignup(BaseModel):
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8)  # Make optional for Google users
    full_name: Optional[str]
    role: UserRole = UserRole.farmer
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    role: UserRole

class GoogleUserData(BaseModel):
    email: EmailStr
    full_name: str
    google_id: str
    profile_picture: Optional[str] = None
    role: UserRole = UserRole.farmer

class UserResponseWithAuth(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    role: UserRole
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    access_token: str
    token_type: str = "bearer"

class GoogleAuthURL(BaseModel):
    auth_url: str
    
class GoogleCallbackData(BaseModel):
    code: str
    state: Optional[str] = None
