from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.comments.models import Comment
from app.core.exceptions import NotFoundException
from app.organizations.access import ensure_post_in_user_org

from .models import CommentLike, PostLike


class LikeService:
    @staticmethod
    def _ensure_post_for_user(db: Session, post_id: UUID, author_id: UUID | None) -> None:
        if author_id is None:
            raise NotFoundException("Post")
        ensure_post_in_user_org(db, post_id, author_id)

    @staticmethod
    def status(db: Session, post_id: UUID, author_id: UUID | None) -> dict:
        LikeService._ensure_post_for_user(db, post_id, author_id)
        count = (
            db.query(func.count(PostLike.id))
            .filter(PostLike.post_id == post_id)
            .scalar()
        )
        liked = False
        if author_id is not None:
            liked = (
                db.query(PostLike.id)
                .filter(PostLike.post_id == post_id, PostLike.author_id == author_id)
                .first()
                is not None
            )
        return {
            "post_id": post_id,
            "like_count": count,
            "liked": liked,
        }

    @staticmethod
    def like(db: Session, post_id: UUID, author_id: UUID) -> dict:
        LikeService._ensure_post_for_user(db, post_id, author_id)
        db.add(PostLike(post_id=post_id, author_id=author_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return LikeService.status(db, post_id, author_id)

    @staticmethod
    def unlike(db: Session, post_id: UUID, author_id: UUID) -> dict:
        LikeService._ensure_post_for_user(db, post_id, author_id)
        db.query(PostLike).filter(
            PostLike.post_id == post_id, PostLike.author_id == author_id
        ).delete()
        db.commit()
        return LikeService.status(db, post_id, author_id)


class CommentLikeService:
    @staticmethod
    def _ensure_comment_for_user(db: Session, comment_id: UUID, author_id: UUID | None) -> Comment:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException("Comment")
        if author_id is None:
            raise NotFoundException("Comment")
        ensure_post_in_user_org(db, comment.post_id, author_id)
        return comment

    @staticmethod
    def status(db: Session, comment_id: UUID, author_id: UUID | None) -> dict:
        CommentLikeService._ensure_comment_for_user(db, comment_id, author_id)
        count = (
            db.query(func.count(CommentLike.id))
            .filter(CommentLike.comment_id == comment_id)
            .scalar()
        )
        liked = False
        if author_id is not None:
            liked = (
                db.query(CommentLike.id)
                .filter(
                    CommentLike.comment_id == comment_id,
                    CommentLike.author_id == author_id,
                )
                .first()
                is not None
            )
        return {
            "comment_id": comment_id,
            "like_count": count,
            "liked": liked,
        }

    @staticmethod
    def like(db: Session, comment_id: UUID, author_id: UUID) -> dict:
        CommentLikeService._ensure_comment_for_user(db, comment_id, author_id)
        db.add(CommentLike(comment_id=comment_id, author_id=author_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return CommentLikeService.status(db, comment_id, author_id)

    @staticmethod
    def unlike(db: Session, comment_id: UUID, author_id: UUID) -> dict:
        CommentLikeService._ensure_comment_for_user(db, comment_id, author_id)
        db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id, CommentLike.author_id == author_id
        ).delete()
        db.commit()
        return CommentLikeService.status(db, comment_id, author_id)
