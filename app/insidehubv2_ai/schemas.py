from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.posts.constants import CATEGORY_SLUGS, PHOTOGRAPHY_SLUG

DraftLength = Literal["short", "medium", "long"]
DraftTone = Literal["warm", "simple", "lively"]

MIN_PROMPT_LENGTH = 10
MAX_QUESTIONS = 4


class DraftAnswer(BaseModel):
    question: str = Field(max_length=300)
    answer: str = Field(max_length=1000)

    @field_validator("question", "answer")
    @classmethod
    def strip(cls, value: str) -> str:
        return value.strip()


class DraftRequest(BaseModel):
    category: str
    prompt: str = Field(max_length=4000)
    answers: List[DraftAnswer] = Field(default_factory=list, max_length=MAX_QUESTIONS)
    length: DraftLength = "medium"
    tone: DraftTone = "warm"
    use_web_search: bool = False

    @field_validator("category")
    @classmethod
    def check_category(cls, value: str) -> str:
        slug = value.strip().lower()
        if slug == PHOTOGRAPHY_SLUG:
            raise ValueError("Photography posts are photos only.")
        if slug not in CATEGORY_SLUGS:
            raise ValueError(f"category must be one of: {', '.join(sorted(CATEGORY_SLUGS))}")
        return slug

    @field_validator("prompt")
    @classmethod
    def check_prompt(cls, value: str) -> str:
        value = value.strip()
        if len(value) < MIN_PROMPT_LENGTH:
            raise ValueError("Tell us a little about what you want to write.")
        return value

    @field_validator("answers")
    @classmethod
    def drop_empty_answers(cls, value: List[DraftAnswer]) -> List[DraftAnswer]:
        return [item for item in value if item.question and item.answer]


class DraftSource(BaseModel):
    title: str
    url: str


class DraftResponse(BaseModel):
    status: Literal["draft", "questions"]
    title: Optional[str] = None
    content: Optional[str] = None
    questions: List[str] = []
    sources: List[DraftSource] = []
    remaining_today: int


class DraftUsage(BaseModel):
    limit: int
    used: int
    remaining: int
    web_search_categories: List[str]
