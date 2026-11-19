import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException

from .constants import OrganizationRole
from .models import Organization, OrganizationMember
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
        user_id: UUID,
    ) -> OrganizationResponse:
        slug = data.slug or _slugify(data.name)
        if OrganizationRepository.get_by_slug(db, slug):
            raise ConflictException(f"Organization slug '{slug}' is already taken")

        organization = Organization(
            name=data.name,
            slug=slug,
            created_by_id=user_id,
        )
        owner_member = OrganizationMember(
            user_id=user_id,
            role=OrganizationRole.OWNER.value,
        )
        org = OrganizationRepository.create(db, organization, owner_member)
        return OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            created_by_id=org.created_by_id,
            role=OrganizationRole.OWNER.value,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )

    @staticmethod
    def list_mine(db: Session, user_id: UUID) -> list[OrganizationResponse]:
        memberships = OrganizationRepository.list_for_user(db, user_id)
        return [
            OrganizationResponse(
                id=m.organization.id,
                name=m.organization.name,
                slug=m.organization.slug,
                created_by_id=m.organization.created_by_id,
                role=m.role,
                created_at=m.organization.created_at,
                updated_at=m.organization.updated_at,
            )
            for m in memberships
        ]
