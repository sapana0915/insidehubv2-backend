from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, EmailStr


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=200)

    description: Optional[str] = Field(default=None, max_length=2000)
    industry: Optional[str] = Field(default=None, max_length=200)
    target_audience: Optional[str] = Field(default=None, max_length=200)
    website_url: Optional[str] = Field(default=None, max_length=500)
    brand_keywords: Optional[str] = Field(default=None, max_length=1000)
    email_domain: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Company email domain for auto-join, e.g. acme.com",
    )

    owner_email: EmailStr
    owner_username: str = Field(min_length=3, max_length=100)
    owner_password: str = Field(min_length=8)
    owner_full_name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("slug")
    @classmethod
    def clean_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().lower().replace(" ", "-")
        if not value:
            raise ValueError("Slug can not be Empty")
        return value

    @field_validator("email_domain")
    @classmethod
    def clean_email_domain(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        # Soft normalize here; full validation (blocked domains) happens in the service.
        domain = value.strip().lower()
        if domain.startswith("@"):
            domain = domain[1:]
        return domain or None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    industry: Optional[str] = Field(default=None, max_length=200)
    target_audience: Optional[str] = Field(default=None, max_length=200)
    website_url: Optional[str] = Field(default=None, max_length=500)
    brand_keywords: Optional[str] = Field(default=None, max_length=1000)
    email_domain: Optional[str] = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("email_domain")
    @classmethod
    def clean_email_domain(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        domain = str(value).strip().lower()
        if domain.startswith("@"):
            domain = domain[1:]
        return domain or None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str

    description: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    website_url: Optional[str] = None
    brand_keywords: Optional[str] = None
    email_domain: Optional[str] = None

    created_by_id: UUID
    role: Optional[str] = None  # caller's role in this org
    owner_email: Optional[EmailStr] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    org_role: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationAdminResponse(BaseModel):
    id: UUID
    name: str
    slug: str

    description: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    website_url: Optional[str] = None
    brand_keywords: Optional[str] = None
    email_domain: Optional[str] = None

    created_by_id: UUID
    member_count: int
    created_at: datetime
    updated_at: datetime
