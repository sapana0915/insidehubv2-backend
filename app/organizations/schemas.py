from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=200)

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


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_by_id: UUID
    role: Optional[str] = None  # caller's role in this org
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
