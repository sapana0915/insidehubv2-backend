from uuid import UUID

from pydantic import BaseModel


class PostLikeStatus(BaseModel):
    post_id: UUID
    like_count: int
    liked: bool


class CommentLikeStatus(BaseModel):
    comment_id: UUID
    like_count: int
    liked: bool
