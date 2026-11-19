from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.request import RequestWrapper, get_request_wrapper

from .schemas import OrganizationCreate, OrganizationResponse
from .services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", response_model=OrganizationResponse)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    return OrganizationService.create(db, data, request.get_user_id())


@router.get("/mine", response_model=list[OrganizationResponse])
def list_my_organizations(
    db: Session = Depends(get_db),
    request: RequestWrapper = Depends(get_request_wrapper),
):
    return OrganizationService.list_mine(db, request.get_user_id())
