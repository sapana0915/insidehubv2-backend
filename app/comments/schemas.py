from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import MAX_COMMENT_LENGTH


def _clean_content(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Comment cannot be empty")
    return value


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_COMMENT_LENGTH)
    post_id: UUID
    author_id: Optional[UUID] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _clean_content(value)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_COMMENT_LENGTH)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _clean_content(value)


class CommentAuthor(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    author_id: UUID
    author: Optional[CommentAuthor] = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
