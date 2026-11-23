from typing import Any, ClassVar, Dict, Optional
from uuid import UUID

from sqlalchemy import exists, or_
from sqlalchemy.orm import Query

from app.core.filters import BaseFilter


from .models import PostImage
from app.users.models import User


class PostFilter(BaseFilter):
    """Filter parameters for post list."""

    _lookups: ClassVar[Dict[str, str]] = {
        "title": "icontains",
        "category": "eq",
    }

    title: Optional[str] = None
    category: Optional[str] = None
    author_id: Optional[UUID] = None
    search: Optional[str] = None

    def apply(self, query: Query, model: Any) -> Query:
        query = super().apply(query, model)
        if self.search:
            term = f"%{self.search.strip()}%"
            place_match = exists().where(
                PostImage.post_id == model.id,
                PostImage.place_name.ilike(term),
            )
            author_match = exists().where(
                User.id == model.author_id,
                or_(User.full_name.ilike(term), User.username.ilike(term))
            )
            query = query.filter(
                or_(model.title.ilike(term), model.content.ilike(term),
                    author_match,
                    place_match)
            )
        return query
