from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.request import RequestWrapper, get_request_wrapper

from .schemas import (
    OrganizationAdminResponse,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationMemberUpdate,
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
    """Platform admin: create an organization and its owner."""
    return OrganizationService.create(db, data, request.get_user_id())


@router.get("/", response_model=list[OrganizationAdminResponse])
def get_organizations(
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Platform admin: list all organizations."""
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


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Platform admin: delete an organization and its posts/prompt logs."""
    OrganizationService.delete_for_admin(db, request.get_user_id(), organization_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
)
def list_organization_members(
    organization_id: UUID,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Admin (any org) or organization owner (their org): list members."""
    return OrganizationService.list_members(
        db,
        request.get_user_id(),
        organization_id,
    )


@router.patch(
    "/{organization_id}/members/{member_user_id}",
    response_model=OrganizationMemberResponse,
)
def update_organization_member(
    organization_id: UUID,
    member_user_id: UUID,
    data: OrganizationMemberUpdate,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Organization owner only: update a member's role or active status."""
    return OrganizationService.update_member_for_owner(
        db,
        request.get_user_id(),
        organization_id,
        member_user_id,
        data,
    )


@router.delete(
    "/{organization_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_organization_member(
    organization_id: UUID,
    member_user_id: UUID,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    """Organization owner only: remove a member from the organization."""
    OrganizationService.remove_member_for_owner(
        db,
        request.get_user_id(),
        organization_id,
        member_user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
