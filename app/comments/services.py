from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException, ValidationException
from app.likes.models import CommentLike
from app.organizations.access import ensure_post_in_user_org, get_user
from app.posts.models import Post

from .models import Comment
from .repositories import CommentRepository
from .schemas import CommentCreate, CommentUpdate


class CommentService:
    model = Comment

    @staticmethod
    def get(db: Session, comment_id: UUID, request: Any = None) -> Comment:
        comment = CommentRepository.get_by_id(db, comment_id)
        if request is not None and getattr(request, "is_authenticated", False):
            ensure_post_in_user_org(db, comment.post_id, request.get_user_id())
        return comment

    @staticmethod
    def _reply_count(db: Session, comment_id: UUID) -> int:
        return (
            db.query(func.count(Comment.id))
            .filter(Comment.parent_id == comment_id)
            .scalar()
        )

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        filters: Any = None,
        request: Any = None,
        viewset: Any = None,
    ) -> list:
        query = db.query(Comment).options(selectinload(Comment.author))
        if request is not None and getattr(request, "is_authenticated", False):
            user = get_user(db, request.get_user_id())
            if user.organization_id:
                query = query.join(Post, Comment.post_id == Post.id).filter(
                    Post.organization_id == user.organization_id
                )
            elif not user.is_admin:
                return []
        else:
            return []
        if filters:
            query = filters.apply(query, Comment)
        if getattr(filters, "parent_id", None) is None:
            query = query.filter(Comment.parent_id.is_(None))
        if viewset and viewset.scope_list_to_owner(request):
            column = getattr(Comment, viewset.owner_field)
            uid = viewset._get_user_id(request)
            query = query.filter(column == uid)
        query = query.order_by(Comment.created_at.asc(), Comment.id)
        comments = query.offset(skip).limit(limit).all()

        ids = [comment.id for comment in comments]
        counts = {}
        reply_counts = {}
        liked_ids = set()
        if ids:
            counts = dict(
                db.query(CommentLike.comment_id, func.count(CommentLike.id))
                .filter(CommentLike.comment_id.in_(ids))
                .group_by(CommentLike.comment_id)
                .all()
            )
            reply_counts = dict(
                db.query(Comment.parent_id, func.count(Comment.id))
                .filter(Comment.parent_id.in_(ids))
                .group_by(Comment.parent_id)
                .all()
            )
            if request is not None and request.is_authenticated:
                liked_ids = {
                    row[0]
                    for row in db.query(CommentLike.comment_id)
                    .filter(
                        CommentLike.comment_id.in_(ids),
                        CommentLike.author_id == request.get_user_id(),
                    )
                    .all()
                }
        for comment in comments:
            comment.like_count = counts.get(comment.id, 0)
            comment.liked = comment.id in liked_ids
            comment.reply_count = reply_counts.get(comment.id, 0)
        return comments

    @staticmethod
    def create(db: Session, comment_data: CommentCreate) -> Comment:
        ensure_post_in_user_org(db, comment_data.post_id, comment_data.author_id)

        parent_id = comment_data.parent_id
        if parent_id is not None:
            parent = (
                db.query(Comment.id, Comment.post_id, Comment.parent_id)
                .filter(Comment.id == parent_id)
                .first()
            )
            if not parent:
                raise NotFoundException("Parent comment not found")
            if parent.post_id != comment_data.post_id:
                raise ValidationException("reply must belong to the same post")
            parent_id = parent.parent_id or parent.id

        comment = Comment(
            content=comment_data.content,
            post_id=comment_data.post_id,
            author_id=comment_data.author_id,
            parent_id=parent_id,
        )
        return CommentRepository.create(db, comment)

    @staticmethod
    def update(db: Session, comment_id: UUID, comment_data: CommentUpdate) -> Comment:
        comment = CommentRepository.get_by_id(db, comment_id)
        comment.content = comment_data.content
        comment = CommentRepository.update(db, comment)
        comment.reply_count = CommentService._reply_count(db, comment_id)
        return comment

    @staticmethod
    def partial_update(
        db: Session, comment_id: UUID, comment_data: CommentUpdate
    ) -> Comment:
        return CommentService.update(db, comment_id, comment_data)

    @staticmethod
    def delete(db: Session, comment_id: UUID) -> None:
        CommentRepository.delete(db, comment_id)
