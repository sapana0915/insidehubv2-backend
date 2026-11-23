from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException
from app.users.models import User

from .models import Organization


class OrganizationRepository:
    @staticmethod
    def get_by_id(db: Session, organization_id: UUID) -> Organization:
        org = (
            db.query(Organization)
            .options(selectinload(Organization.users))
            .filter(Organization.id == organization_id)
            .first()
        )
        if not org:
            raise NotFoundException("Organization")
        return org

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Organization | None:
        return db.query(Organization).filter(Organization.slug == slug).first()

    @staticmethod
    def get_for_user(db: Session, user_id: UUID) -> Organization | None:
        """One user → at most one organization (via users.organization_id)."""
        user = (
            db.query(User)
            .options(selectinload(User.organization))
            .filter(User.id == user_id)
            .first()
        )
        if not user or not user.organization_id:
            return None
        return user.organization

    @staticmethod
    def create(db: Session, organization: Organization) -> Organization:
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return OrganizationRepository.get_by_id(db, organization.id)

    @staticmethod
    def create_with_owner(
        db: Session,
        organization: Organization,
        owner: User,
    ) -> tuple[Organization, User]:
        db.add(organization)
        db.flush()  # organization.id available
        owner.organization_id = organization.id
        owner.org_role = "owner"
        db.add(owner)
        db.commit()
        db.refresh(organization)
        db.refresh(owner)
        return organization, owner