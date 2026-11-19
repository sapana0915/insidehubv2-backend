from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException

from .models import Organization, OrganizationMember


class OrganizationRepository:
    @staticmethod
    def get_by_id(db: Session, organization_id: UUID) -> Organization:
        org = (
            db.query(Organization)
            .options(selectinload(Organization.members))
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
    def list_for_user(db: Session, user_id: UUID) -> list[OrganizationMember]:
        return (
            db.query(OrganizationMember)
            .options(selectinload(OrganizationMember.organization))
            .filter(OrganizationMember.user_id == user_id)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        organization: Organization,
        owner_member: OrganizationMember,
    ) -> Organization:
        db.add(organization)
        db.flush()  # get organization.id before member insert
        owner_member.organization_id = organization.id
        db.add(owner_member)
        db.commit()
        db.refresh(organization)
        return OrganizationRepository.get_by_id(db, organization.id)

    @staticmethod
    def get_membership(
        db: Session,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMember | None:
        return (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )
