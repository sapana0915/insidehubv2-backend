from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.request import (
    RequestWrapper,
    get_optional_request_wrapper,
    get_request_wrapper,
)

from .schemas import PostLikeStatus, CommentLikeStatus
from .services import LikeService, CommentLikeService

router = APIRouter(prefix="/posts", tags=["likes"])
comment_likes_router = APIRouter(prefix="/comments", tags=["comment-likes"])


@router.get("/{post_id}/likes", response_model=PostLikeStatus)
def get_likes(
    post_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_optional_request_wrapper),
):
    author_id = wrapper.get_user_id() if wrapper.is_authenticated else None
    return LikeService.status(db, post_id, author_id)


@router.post("/{post_id}/like", response_model=PostLikeStatus)
def like_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_request_wrapper),
):
    return LikeService.like(db, post_id, wrapper.get_user_id())


@router.delete("/{post_id}/like", response_model=PostLikeStatus)
def unlike_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_request_wrapper),
):
    return LikeService.unlike(db, post_id, wrapper.get_user_id())

@comment_likes_router.get("/{comment_id}/likes", response_model=CommentLikeStatus)
def get_comments_likes(
    comment_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_optional_request_wrapper),
):
    author_id = wrapper.get_user_id() if wrapper.is_authenticated else None
    return CommentLikeService.status(db, comment_id, author_id)


@comment_likes_router.post("/{comment_id}/like", response_model=CommentLikeStatus)
def like_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_request_wrapper),
):
    return CommentLikeService.like(db, comment_id, wrapper.get_user_id())


@comment_likes_router.delete("/{comment_id}/like", response_model=CommentLikeStatus)
def unlike_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    wrapper: RequestWrapper = Depends(get_request_wrapper),
):
    return CommentLikeService.unlike(db, comment_id, wrapper.get_user_id())
