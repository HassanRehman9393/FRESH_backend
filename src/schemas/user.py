from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    farmer = "farmer"
    exporter = "exporter"
    government = "government"
    admin = "admin"

class UserSignup(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    full_name: Optional[str]
    role: UserRole = UserRole.farmer

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    role: UserRole
