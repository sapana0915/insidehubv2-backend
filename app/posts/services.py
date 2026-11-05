from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ValidationException

from .constants import PHOTOGRAPHY_SLUG
from .models import Post
from .repositories import PostRepository
from .schemas import PostCreate, PostUpdate


class PostService:
    model = Post

    @staticmethod
    def get(db: Session, post_id: UUID) -> Post:
        return PostRepository.get_by_id(db, post_id)

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        filters: Any = None,
        request: Any = None,
        viewset: Any = None,
    ) -> list:
        query = db.query(Post).options(
            selectinload(Post.images), selectinload(Post.author)
        )
        if filters:
            query = filters.apply(query, Post)
        if viewset and viewset.scope_list_to_owner(request):
            column = getattr(Post, viewset.owner_field)
            uid = viewset._get_user_id(request)
            query = query.filter(column == uid)
        query = query.order_by(Post.created_at.desc(), Post.id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, post_data: PostCreate) -> Post:
        post = Post(
            title=post_data.title,
            content=post_data.content,
            category=post_data.category,
            author_id=post_data.author_id,
        )
        if post_data.images:
            PostRepository.replace_images(
                db,
                post,
                post_data.images,
                post_data.author_id,
                keep_places=post_data.category == PHOTOGRAPHY_SLUG,
            )
        return PostRepository.create(db, post)

    @staticmethod
    def update(db: Session, post_id: UUID, post_data: PostUpdate) -> Post:
        post = PostRepository.get_by_id(db, post_id)
        category = post_data.category if post_data.category is not None else post.category

        if category == PHOTOGRAPHY_SLUG:
            if post_data.images is not None and len(post_data.images) == 0:
                raise ValidationException("Photography posts need at least one photo.")
            if post_data.images is None and len(post.images) == 0:
                raise ValidationException("Photography posts need at least one photo.")
            post.title = ""
            post.content = ""
            post.category = category
            if post_data.images is not None:
                PostRepository.replace_images(
                    db, post, post_data.images, post.author_id, keep_places=True
                )
            return PostRepository.update(db, post)

        title = post.title if post_data.title is None else post_data.title
        content = post.content if post_data.content is None else post_data.content
        title = title.strip()
        content = content.strip()
        if not title or not content:
            raise ValidationException("Every entry needs a title and a story.")
        post.title = title
        post.content = content
        post.category = category
        if post_data.images is not None:
            PostRepository.replace_images(
                db, post, post_data.images, post.author_id, keep_places=False
            )
        else:
            for image in post.images:
                image.place_name = None

        return PostRepository.update(db, post)

    @staticmethod
    def partial_update(
        db: Session, post_id: UUID, post_data: PostUpdate
    ) -> Post:
        return PostService.update(db, post_id, post_data)

    @staticmethod
    def delete(db: Session, post_id: UUID) -> None:
        PostRepository.delete(db, post_id)
