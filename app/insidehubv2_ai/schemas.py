from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.posts.constants import CATEGORY_SLUGS, PHOTOGRAPHY_SLUG

DraftLength = Literal["short", "medium", "long"]
DraftTone = Literal["warm", "simple", "lively"]

MIN_NOTES_LENGTH = 20


class DraftRequest(BaseModel):
    category: str
    notes: str = Field(max_length=4000)
    where: Optional[str] = Field(default=None, max_length=200)
    when: Optional[str] = Field(default=None, max_length=200)
    who: Optional[str] = Field(default=None, max_length=200)
    detail: Optional[str] = Field(default=None, max_length=500)
    feeling: Optional[str] = Field(default=None, max_length=300)
    length: DraftLength = "medium"
    tone: DraftTone = "warm"

    @field_validator("category")
    @classmethod
    def check_category(cls, value: str) -> str:
        slug = value.strip().lower()
        if slug == PHOTOGRAPHY_SLUG:
            raise ValueError("Photography posts are photos only.")
        if slug not in CATEGORY_SLUGS:
            raise ValueError(f"category must be one of: {', '.join(sorted(CATEGORY_SLUGS))}")
        return slug

    @field_validator("notes")
    @classmethod
    def check_notes(cls, value: str) -> str:
        value = value.strip()
        if len(value) < MIN_NOTES_LENGTH:
            raise ValueError("Tell a little more about what happened. A sentence or two is enough.")
        return value

    @field_validator("where", "when", "who", "detail", "feeling")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class DraftResponse(BaseModel):
    title: str
    content: str
    remaining_today: int


class DraftUsage(BaseModel):
    limit: int
    used: int
    remaining: int