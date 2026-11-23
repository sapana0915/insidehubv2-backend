import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException
from app.core.security import hash_password
from app.users.models import User
from app.users.repositories import UserRepository

from .models import Organization
from .repositories import OrganizationRepository
from .schemas import OrganizationCreate, OrganizationResponse


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "org"


class OrganizationService:
    @staticmethod
    def create(
        db: Session,
        data: OrganizationCreate,
        admin_user_id: UUID,
    ) -> OrganizationResponse:
        admin = UserRepository.get_by_id(db, admin_user_id)
        if not admin.is_admin:
            raise ForbiddenException("Only an admin can create an organization")

        slug = data.slug or _slugify(data.name)
        if OrganizationRepository.get_by_slug(db, slug):
            raise ConflictException(f"Organization slug '{slug}' is already taken")

        email = data.owner_email.lower()
        if UserRepository.get_by_email(db, email):
            raise ConflictException("Owner email already registered")
        if UserRepository.get_by_username(db, data.owner_username):
            raise ConflictException("Owner username already taken")

        organization = Organization(
            name=data.name,
            slug=slug,
            created_by_id=admin_user_id,
        )
        owner = User(
            email=email,
            username=data.owner_username,
            full_name=data.owner_full_name,
            hashed_password=hash_password(data.owner_password),
            # organization_id / org_role set in repository after flush
        )
        org, owner = OrganizationRepository.create_with_owner(db, organization, owner)

        return OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            created_by_id=org.created_by_id,
            role=None,  # admin is not a member
            owner_email=owner.email,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )

    @staticmethod
    def list_mine(db: Session, user_id: UUID) -> list[OrganizationResponse]:
        user = UserRepository.get_by_id(db, user_id)
        org = OrganizationRepository.get_for_user(db, user_id)
        if not org:
            return []
        return [
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                created_by_id=org.created_by_id,
                role=user.org_role,
                owner_email=None,
                created_at=org.created_at,
                updated_at=org.updated_at,
            )
        ]
