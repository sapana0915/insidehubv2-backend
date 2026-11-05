from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException
from app.posts.models import Post

from .models import Comment
from .repositories import CommentRepository
from .schemas import CommentCreate, CommentUpdate


class CommentService:
    model = Comment

    @staticmethod
    def get(db: Session, comment_id: UUID) -> Comment:
        return CommentRepository.get_by_id(db, comment_id)

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
        if filters:
            query = filters.apply(query, Comment)
        if viewset and viewset.scope_list_to_owner(request):
            column = getattr(Comment, viewset.owner_field)
            uid = viewset._get_user_id(request)
            query = query.filter(column == uid)
        query = query.order_by(Comment.created_at.asc(), Comment.id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, comment_data: CommentCreate) -> Comment:
        post = db.query(Post.id).filter(Post.id == comment_data.post_id).first()
        if not post:
            raise NotFoundException("Post")

        comment = Comment(
            content=comment_data.content,
            post_id=comment_data.post_id,
            author_id=comment_data.author_id,
        )
        return CommentRepository.create(db, comment)

    @staticmethod
    def update(db: Session, comment_id: UUID, comment_data: CommentUpdate) -> Comment:
        comment = CommentRepository.get_by_id(db, comment_id)
        comment.content = comment_data.content
        return CommentRepository.update(db, comment)

    @staticmethod
    def partial_update(
        db: Session, comment_id: UUID, comment_data: CommentUpdate
    ) -> Comment:
        return CommentService.update(db, comment_id, comment_data)

    @staticmethod
    def delete(db: Session, comment_id: UUID) -> None:
        CommentRepository.delete(db, comment_id)
