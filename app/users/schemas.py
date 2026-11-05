from uuid import UUID

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    code: str = Field(min_length=6, max_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicUserResponse(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None
    created_at: datetime
    post_count: int = 0

    class Config:
        from_attributes = True


class SendCodeRequest(BaseModel):
    email: EmailStr
    username: str


class SendCodeResponse(BaseModel):
    message: str
    expires_in: int
    resend_in: int


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
