from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.comments.models import Comment
from app.core.exceptions import NotFoundException
from app.posts.models import Post

from .models import PostLike, CommentLike


class LikeService:
    @staticmethod
    def _ensure_post(db: Session, post_id: UUID) -> None:
        if not db.query(Post).filter(Post.id == post_id).first():
            raise NotFoundException("Post")

    @staticmethod
    def status(db: Session, post_id: UUID, author_id: UUID | None) -> dict:
        LikeService._ensure_post(db, post_id)
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
                .first() is not None
            )
        return {
            "post_id": post_id,
            "like_count": count,
            "liked": liked
            }

    @staticmethod
    def like(db: Session, post_id: UUID, author_id: UUID) -> dict:
        LikeService._ensure_post(db, post_id)
        db.add(PostLike(post_id=post_id, author_id=author_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return LikeService.status(db, post_id, author_id)

    @staticmethod
    def unlike(db: Session, post_id: UUID, author_id: UUID) -> dict:
        LikeService._ensure_post(db, post_id)
        db.query(PostLike).filter(
            PostLike.post_id == post_id, PostLike.author_id == author_id
        ).delete()
        db.commit()
        return LikeService.status(db, post_id, author_id)


class CommentLikeService:
    @staticmethod
    def _ensure_comment(db: Session, comment_id: UUID) -> None:
        if not db.query(Comment.id).filter(Comment.id == comment_id).first():
            raise NotFoundException("Comment")

    @staticmethod
    def status(db: Session, comment_id: UUID, author_id: UUID | None) -> dict:
        CommentLikeService._ensure_comment(db, comment_id)
        count = (
            db.query(func.count(CommentLike.id))
            .filter(CommentLike.comment_id == comment_id)
            .scalar()
        )
        liked = False
        if author_id is not None:
            liked = (
                db.query(CommentLike.id)
                .filter(CommentLike.comment_id == comment_id, CommentLike.author_id == author_id)
                .first() is not None
            )
        return {
            "comment_id": comment_id,
            "like_count": count,
            "liked": liked,
        }

    @staticmethod
    def like(db: Session, comment_id: UUID, author_id: UUID) -> dict:
        CommentLikeService._ensure_comment(db, comment_id)
        db.add(CommentLike(comment_id=comment_id, author_id=author_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return CommentLikeService.status(db, comment_id, author_id)

    @staticmethod
    def unlike(db: Session, comment_id: UUID, author_id: UUID) -> dict:
        CommentLikeService._ensure_comment(db, comment_id)
        db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id, CommentLike.author_id == author_id
        ).delete()
        db.commit()
        return CommentLikeService.status(db, comment_id, author_id)
