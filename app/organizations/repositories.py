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
    def get_by_email_domain(db: Session, email_domain: str) -> Organization | None:
        return (
            db.query(Organization)
            .filter(Organization.email_domain == email_domain)
            .first()
        )

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

    @staticmethod
    def list_all(db: Session) -> list[Organization]:
        return db.query(Organization).order_by(Organization.name.asc()).all()

    @staticmethod
    def count_members(db: Session, organization_id: UUID) -> int:
        return db.query(User).filter(User.organization_id == organization_id).count()

    @staticmethod
    def list_members(db: Session, organization_id: UUID) -> list[User]:
        return (
            db.query(User)
            .filter(User.organization_id == organization_id)
            .order_by(User.org_role.asc(), User.username.asc())
            .all()
        )

    @staticmethod
    def update(db: Session, org: Organization) -> Organization:
        db.add(org)
        db.commit()
        db.refresh(org)
        return org

    @staticmethod
    def delete(db: Session, org: Organization) -> None:
        db.delete(org)
        db.commit()

    @staticmethod
    def get_member(
        db: Session,
        organization_id: UUID,
        member_user_id: UUID,
    ) -> User:
        user = (
            db.query(User)
            .filter(
                User.id == member_user_id,
                User.organization_id == organization_id,
            )
            .first()
        )
        if not user:
            raise NotFoundException("Organization member")
        return user

