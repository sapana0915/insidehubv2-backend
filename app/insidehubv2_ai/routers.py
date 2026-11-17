from fastapi import APIRouter, Depends

from app.middleware.request import RequestWrapper, get_request_wrapper

from .schemas import DraftRequest, DraftResponse, DraftUsage
from .services import draft_for_user, usage_for_user

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/drafts/usage", response_model=DraftUsage)
async def get_draft_usage(wrapper: RequestWrapper = Depends(get_request_wrapper)):
    """How many drafts the current user has left today."""
    return await usage_for_user(wrapper.get_user_id())


@router.post("/drafts", response_model=DraftResponse)
async def create_draft(
    body: DraftRequest,
    wrapper: RequestWrapper = Depends(get_request_wrapper),
):
    """Turn a person's notes into a title and story. Does not save a post."""
    return await draft_for_user(wrapper.get_user_id(), body)
