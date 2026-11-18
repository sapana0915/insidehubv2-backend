from typing import Optional
from uuid import UUID

from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.users.repositories import UserRepository

from app.core.security import get_token_payload
from app.core.exceptions import UnauthorizedException


class RequestWrapper:
    """
    Wrapper to access request context similar to Django's Request object.
    Provides easy access to authenticated user.
    """

    def __init__(self, request: Request, user: Optional[dict] = None):
        self.request = request
        self._user = user

    @property
    def user(self) -> dict:
        if self._user is None:
            raise UnauthorizedException("User not authenticated")
        return self._user

    @property
    def headers(self) -> dict:
        return dict(self.request.headers)

    @property
    def query_params(self) -> dict:
        return dict(self.request.query_params)

    async def json(self) -> dict:
        return await self.request.json()

    async def form(self) -> dict:
        return dict(await self.request.form())

    def get_user_id(self) -> UUID:
        uid = self.user.get("user_id") or self.user.get("sub")
        return UUID(str(uid))

    def get_user_role(self) -> str:
        return self.user.get("role")

    @property
    def is_authenticated(self) -> bool:
        return self._user is not None


async def get_request_wrapper(
    request: Request,
    token_payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> RequestWrapper:
    user_id = token_payload.get("user_id") or token_payload.get("sub")
    user = UserRepository.get_by_id(db, UUID(str(user_id)))
    if not user.is_active:
        raise UnauthorizedException("User is inactive")
    return RequestWrapper(request, user=token_payload)


async def get_optional_request_wrapper(
    request: Request,
    db: Session = Depends(get_db),
) -> RequestWrapper:
    from app.core.security import decode_token

    user_payload = None
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = decode_token(token)
            user_id = payload.get("user_id") or payload.get("sub")
            db_user = UserRepository.get_by_id(db, UUID(str(user_id)))
            if not db_user.is_active:
                raise UnauthorizedException("User is inactive")
            user_payload = payload
        except UnauthorizedException:
            raise
        # optionally catch NotFoundException and leave user_payload = None
    return RequestWrapper(request, user=user_payload)
