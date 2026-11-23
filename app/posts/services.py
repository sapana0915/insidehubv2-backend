from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.organizations.access import get_user, post_visible_to_user
from app.users.repositories import UserRepository

from .constants import PHOTOGRAPHY_SLUG
from .html_sanitize import is_blank_html, sanitize_post_html
from .models import Post
from .repositories import PostRepository
from .schemas import PostCreate, PostUpdate


class PostService:
    model = Post

    @staticmethod
    def get(db: Session, post_id: UUID, request: Any = None) -> Post:
        post = PostRepository.get_by_id(db, post_id)
        if request is not None and getattr(request, "is_authenticated", False):
            user = get_user(db, request.get_user_id())
            if not post_visible_to_user(post, user):
                raise NotFoundException("Post")
        elif request is not None:
            raise NotFoundException("Post")
        return post

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
        if request is None or not getattr(request, "is_authenticated", False):
            return []
        user = get_user(db, request.get_user_id())
        if user.organization_id:
            query = query.filter(Post.organization_id == user.organization_id)
        elif not user.is_admin:
            return []
        # Platform admin with no org sees all orgs (support).
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
        author = UserRepository.get_by_id(db, post_data.author_id)
        if not author.organization_id:
            raise ForbiddenException("You must belong to an organization to post")

        post = Post(
            title=post_data.title,
            content=post_data.content,
            category=post_data.category,
            author_id=post_data.author_id,
            organization_id=author.organization_id,
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
        content = sanitize_post_html(content)
        if not title or is_blank_html(content):
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
