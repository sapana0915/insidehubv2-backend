from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime

from .constants import CATEGORY_SLUGS, PHOTOGRAPHY_SLUG

MAX_IMAGES_PER_POST = 12


def _validate_category(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    slug = value.strip().lower()
    if slug not in CATEGORY_SLUGS:
        raise ValueError(f"category must be one of: {', '.join(sorted(CATEGORY_SLUGS))}")
    return slug


def _coerce_images(value: Any) -> Any:
    if not value:
        return value
    coerced = []
    for item in value:
        if isinstance(item, str):
            coerced.append({"url": item})
        else:
            coerced.append(item)
    return coerced


class PostImageIn(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    place_name: Optional[str] = Field(default=None, max_length=200)

    @field_validator("url")
    @classmethod
    def clean_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("image url is required")
        return value

    @field_validator("place_name")
    @classmethod
    def clean_place_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PostBase(BaseModel):
    title: str = Field(default="", max_length=200)
    content: str = Field(default="")
    category: str

    @field_validator("category")
    @classmethod
    def check_category(cls, value: str) -> str:
        return _validate_category(value)


class PostCreate(PostBase):
    author_id: Optional[UUID] = None
    images: Optional[List[PostImageIn]] = Field(default=None, max_length=MAX_IMAGES_PER_POST)

    @field_validator("images", mode="before")
    @classmethod
    def coerce_images(cls, value: Any) -> Any:
        return _coerce_images(value)

    @model_validator(mode="after")
    def enforce_category_shape(self):
        if self.category == PHOTOGRAPHY_SLUG:
            if not self.images:
                raise ValueError("Photography posts need at least one photo.")
            self.title = ""
            self.content = ""
            return self

        title = self.title.strip()
        content = self.content.strip()
        if not title:
            raise ValueError("Every entry needs a title.")
        if not content:
            raise ValueError("Every entry needs a story.")
        self.title = title
        self.content = content
        if self.images:
            for image in self.images:
                image.place_name = None
        return self


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    images: Optional[List[PostImageIn]] = Field(default=None, max_length=MAX_IMAGES_PER_POST)

    @field_validator("category")
    @classmethod
    def check_category(cls, value: Optional[str]) -> Optional[str]:
        return _validate_category(value)

    @field_validator("images", mode="before")
    @classmethod
    def coerce_images(cls, value: Any) -> Any:
        return _coerce_images(value)


class PostImageResponse(BaseModel):
    id: UUID
    image_url: str
    place_name: Optional[str] = None
    user_id: UUID

    class Config:
        from_attributes = True


class PostAuthor(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    author_id: UUID
    author: Optional[PostAuthor] = None
    images: List[PostImageResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    slug: str
    name: str
    description: str


class UploadResponse(BaseModel):
    url: str
