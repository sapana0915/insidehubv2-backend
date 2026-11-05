from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException

from .models import Comment


class CommentRepository:
    @staticmethod
    def get_by_id(db: Session, comment_id: UUID) -> Comment:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException("Comment")
        return comment

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 10) -> list:
        return (
            db.query(Comment)
            .order_by(Comment.created_at.asc(), Comment.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, comment: Comment) -> Comment:
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def update(db: Session, comment: Comment) -> Comment:
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def delete(db: Session, comment_id: UUID) -> None:
        comment = CommentRepository.get_by_id(db, comment_id)
        db.delete(comment)
        db.commit()
