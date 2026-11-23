"""Helpers to enforce one-organization-per-user post visibility."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.posts.models import Post
from app.users.models import User
from app.users.repositories import UserRepository


def get_user(db: Session, user_id: UUID) -> User:
    return UserRepository.get_by_id(db, user_id)


def require_organization_member(db: Session, user_id: UUID) -> User:
    """Return the user; raise if they have no organization."""
    user = get_user(db, user_id)
    if user.is_admin and not user.organization_id:
        raise ForbiddenException("Platform admins are not members of an organization feed")
    if not user.organization_id:
        raise ForbiddenException("You must belong to an organization")
    return user


def post_visible_to_user(post: Post, user: User) -> bool:
    if user.is_admin and not user.organization_id:
        return True
    return bool(user.organization_id) and post.organization_id == user.organization_id


def ensure_post_in_user_org(db: Session, post_id: UUID, user_id: UUID) -> Post:
    """Load a post; 404 if missing or not in the caller's organization."""
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise NotFoundException("Post")
    user = get_user(db, user_id)
    if not post_visible_to_user(post, user):
        raise NotFoundException("Post")
    return post
