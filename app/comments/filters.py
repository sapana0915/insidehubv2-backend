from typing import ClassVar, Dict, Optional
from uuid import UUID

from app.core.filters import BaseFilter


class CommentFilter(BaseFilter):
    """Filter parameters for comment list."""

    _lookups: ClassVar[Dict[str, str]] = {
        "content": "icontains",
    }

    content: Optional[str] = None
    post_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
