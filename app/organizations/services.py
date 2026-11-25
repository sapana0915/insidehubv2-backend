import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException, ValidationException
from app.core.security import hash_password
from app.insidehubv2_ai.models import AiPromptLog
from app.posts.models import Post
from app.users.models import User
from app.users.repositories import UserRepository

from .constants import OrganizationRole
from .email_domains import domain_from_email, normalize_email_domain
from .models import Organization
from .repositories import OrganizationRepository
from .schemas import (
    OrganizationAdminResponse,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationMemberUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "org"


def _org_response(
    org: Organization,
    *,
    role: str | None = None,
    owner_email: str | None = None,
) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        industry=org.industry,
        target_audience=org.target_audience,
        website_url=org.website_url,
        brand_keywords=org.brand_keywords,
        email_domain=org.email_domain,
        created_by_id=org.created_by_id,
        role=role,
        owner_email=owner_email,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _admin_response(db: Session, org: Organization) -> OrganizationAdminResponse:
    return OrganizationAdminResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        industry=org.industry,
        target_audience=org.target_audience,
        website_url=org.website_url,
        brand_keywords=org.brand_keywords,
        email_domain=org.email_domain,
        created_by_id=org.created_by_id,
        member_count=OrganizationRepository.count_members(db, org.id),
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _member_response(user: User) -> OrganizationMemberResponse:
    return OrganizationMemberResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        org_role=user.org_role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class OrganizationService:
    @staticmethod
    def create(
        db: Session,
        data: OrganizationCreate,
        admin_user_id: UUID,
    ) -> OrganizationResponse:
        OrganizationService._require_admin(db, admin_user_id)

        slug = data.slug or _slugify(data.name)
        if OrganizationRepository.get_by_slug(db, slug):
            raise ConflictException(f"Organization slug '{slug}' is already taken")

        email = data.owner_email.lower()
        if UserRepository.get_by_email(db, email):
            raise ConflictException("Owner email already registered")
        if UserRepository.get_by_username(db, data.owner_username):
            raise ConflictException("Owner username already taken")

        if data.email_domain:
            email_domain = normalize_email_domain(data.email_domain)
        else:
            try:
                email_domain = normalize_email_domain(domain_from_email(email))
            except ValidationException as exc:
                raise ValidationException(
                    "Set email_domain to your company domain "
                    "(public emails like gmail.com cannot be used for auto-join)."
                ) from exc
        if not email_domain:
            raise ValidationException("email_domain is required for member auto-join")
        if OrganizationRepository.get_by_email_domain(db, email_domain):
            raise ConflictException(
                f"Email domain '{email_domain}' is already used by another organization"
            )

        organization = Organization(
            name=data.name,
            slug=slug,
            created_by_id=admin_user_id,
            description=data.description,
            industry=data.industry,
            target_audience=data.target_audience,
            website_url=data.website_url,
            brand_keywords=data.brand_keywords,
            email_domain=email_domain,
        )
        owner = User(
            email=email,
            username=data.owner_username,
            full_name=data.owner_full_name,
            hashed_password=hash_password(data.owner_password),
        )
        org, owner = OrganizationRepository.create_with_owner(db, organization, owner)
        return _org_response(org, owner_email=owner.email)

    @staticmethod
    def list_mine(db: Session, user_id: UUID) -> list[OrganizationResponse]:
        user = UserRepository.get_by_id(db, user_id)
        org = OrganizationRepository.get_for_user(db, user_id)
        if not org:
            return []
        return [_org_response(org, role=user.org_role)]

    @staticmethod
    def _require_admin(db: Session, user_id: UUID) -> User:
        user = UserRepository.get_by_id(db, user_id)
        if not user.is_admin:
            raise ForbiddenException("Only an admin can perform this action")
        return user

    @staticmethod
    def _require_org_owner(db: Session, user_id: UUID, organization_id: UUID) -> User:
        """Org owner only — platform admins cannot manage members."""
        user = UserRepository.get_by_id(db, user_id)
        if user.is_admin and not user.organization_id:
            raise ForbiddenException(
                "Only the organization owner can manage members"
            )
        if (
            user.organization_id != organization_id
            or user.org_role != OrganizationRole.OWNER.value
        ):
            raise ForbiddenException(
                "Only the organization owner can manage members"
            )
        OrganizationRepository.get_by_id(db, organization_id)
        return user

    @staticmethod
    def list_all_for_admin(
        db: Session,
        admin_user_id: UUID,
    ) -> list[OrganizationAdminResponse]:
        OrganizationService._require_admin(db, admin_user_id)
        orgs = OrganizationRepository.list_all(db)
        return [_admin_response(db, org) for org in orgs]

    @staticmethod
    def list_members(
        db: Session,
        caller_id: UUID,
        organization_id: UUID,
    ) -> list[OrganizationMemberResponse]:
        """Admin may view any org's members; owner may view their own."""
        caller = UserRepository.get_by_id(db, caller_id)
        OrganizationRepository.get_by_id(db, organization_id)

        is_admin = caller.is_admin
        is_owner = (
            caller.organization_id == organization_id
            and caller.org_role == OrganizationRole.OWNER.value
        )
        if not is_admin and not is_owner:
            raise ForbiddenException(
                "Only an admin or the organization owner can list members"
            )

        members = OrganizationRepository.list_members(db, organization_id)
        return [_member_response(user) for user in members]

    @staticmethod
    def update_for_admin(
        db: Session,
        admin_user_id: UUID,
        organization_id: UUID,
        data: OrganizationUpdate,
    ) -> OrganizationAdminResponse:
        OrganizationService._require_admin(db, admin_user_id)
        org = OrganizationRepository.get_by_id(db, organization_id)
        payload = data.model_dump(exclude_unset=True)

        if "email_domain" in payload:
            email_domain = normalize_email_domain(payload["email_domain"])
            if email_domain:
                existing = OrganizationRepository.get_by_email_domain(db, email_domain)
                if existing and existing.id != org.id:
                    raise ConflictException(
                        f"Email domain '{email_domain}' is already used by another organization"
                    )
            org.email_domain = email_domain
            payload.pop("email_domain")

        for field, value in payload.items():
            setattr(org, field, value)

        org = OrganizationRepository.update(db, org)
        return _admin_response(db, org)

    @staticmethod
    def delete_for_admin(db: Session, admin_user_id: UUID, organization_id: UUID) -> None:
        OrganizationService._require_admin(db, admin_user_id)
        org = OrganizationRepository.get_by_id(db, organization_id)

        members = OrganizationRepository.list_members(db, organization_id)
        for user in members:
            user.organization_id = None
            user.org_role = None

        posts = db.query(Post).filter(Post.organization_id == organization_id).all()
        for post in posts:
            db.delete(post)

        db.query(AiPromptLog).filter(
            AiPromptLog.organization_id == organization_id
        ).delete(synchronize_session=False)

        db.flush()
        OrganizationRepository.delete(db, org)

    @staticmethod
    def join_by_email(db: Session, user_id: UUID) -> OrganizationResponse:
        user = UserRepository.get_by_id(db, user_id)
        if user.organization_id:
            org = OrganizationRepository.get_by_id(db, user.organization_id)
            return _org_response(org, role=user.org_role)

        domain = domain_from_email(user.email)
        if not domain:
            raise ValidationException("Your email address is invalid")

        org = OrganizationRepository.get_by_email_domain(db, domain)
        if not org:
            raise ValidationException(
                f"No organization is set up for @{domain}. "
                "Ask your admin to create the organization with that email domain."
            )

        user.organization_id = org.id
        user.org_role = OrganizationRole.MEMBER.value
        UserRepository.update(db, user)
        return _org_response(org, role=user.org_role)

    @staticmethod
    def update_member_for_owner(
        db: Session,
        owner_user_id: UUID,
        organization_id: UUID,
        member_user_id: UUID,
        data: OrganizationMemberUpdate,
    ) -> OrganizationMemberResponse:
        owner = OrganizationService._require_org_owner(db, owner_user_id, organization_id)
        if member_user_id == owner.id:
            raise ValidationException("You cannot change your own membership this way")

        member = OrganizationRepository.get_member(db, organization_id, member_user_id)
        if member.org_role == OrganizationRole.OWNER.value:
            raise ForbiddenException("You cannot change the organization owner this way")

        payload = data.model_dump(exclude_unset=True)
        if not payload:
            raise ValidationException("No member fields to update")

        if "org_role" in payload:
            member.org_role = payload["org_role"]
        if "is_active" in payload:
            member.is_active = payload["is_active"]

        UserRepository.update(db, member)
        return _member_response(member)

    @staticmethod
    def remove_member_for_owner(
        db: Session,
        owner_user_id: UUID,
        organization_id: UUID,
        member_user_id: UUID,
    ) -> None:
        owner = OrganizationService._require_org_owner(db, owner_user_id, organization_id)
        if member_user_id == owner.id:
            raise ValidationException("You cannot remove yourself from the organization")

        member = OrganizationRepository.get_member(db, organization_id, member_user_id)
        if member.org_role == OrganizationRole.OWNER.value:
            raise ForbiddenException("You cannot remove the organization owner")

        member.organization_id = None
        member.org_role = None
        UserRepository.update(db, member)
