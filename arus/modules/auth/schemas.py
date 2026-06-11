from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict
    expires_at: datetime


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str = "viewer"
