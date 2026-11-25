from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.request import RequestWrapper, get_request_wrapper

from .schemas import (
    OrganizationAdminResponse,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from .services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", response_model=OrganizationResponse)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    return OrganizationService.create(db, data, request.get_user_id())


@router.get("/", response_model=list[OrganizationAdminResponse])
def get_organizations(
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    return OrganizationService.list_all_for_admin(db, request.get_user_id())


@router.get("/mine", response_model=list[OrganizationResponse])
def list_my_organizations(
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    return OrganizationService.list_mine(db, request.get_user_id())


@router.post("/join", response_model=OrganizationResponse)
def join_organization(
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Join the organization that matches the caller's email domain."""
    return OrganizationService.join_by_email(db, request.get_user_id())


@router.patch("/{organization_id}", response_model=OrganizationAdminResponse)
def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Platform admin: update organization profile / email domain."""
    return OrganizationService.update_for_admin(
        db,
        request.get_user_id(),
        organization_id,
        data,
    )


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
)
def list_organization_members(
    organization_id: UUID,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Platform admin: users in one organization."""
    return OrganizationService.list_members_for_admin(
        db,
        request.get_user_id(),
        organization_id,
    )
