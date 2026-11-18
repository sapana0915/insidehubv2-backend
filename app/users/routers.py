from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

import io
from .exports import build_user_portfolio_pdf
from app.posts.repositories import PostRepository
from app.core.config import settings
from app.core.constants import UserRole
from app.core.exceptions import ConflictException, ForbiddenException
from app.core.security import create_access_token
from app.database import get_db
from app.middleware.request import RequestWrapper, get_request_wrapper
from app.posts.models import Post
from .otp import consume_code, issue_code
from .password_reset import apply_password_reset, request_password_reset
from .repositories import UserRepository
from .schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    PublicUserResponse,
    ResetPasswordRequest,
    SendCodeRequest,
    SendCodeResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from .services import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _token_for(user) -> dict:
    role = UserRole.ADMIN.value if user.is_admin else UserRole.USER.value
    return {
        "access_token": create_access_token(
            data={
                "sub": str(user.id),
                "user_id": str(user.id),
                "email": user.email,
                "role": role,
            },
        ),
        "token_type": "bearer",
    }


@router.post("/register/send-code", response_model=SendCodeResponse)
def send_register_code(data: SendCodeRequest, db: Session = Depends(get_db)):
    """Email a 6-digit code. No account is created yet."""
    email = data.email.lower()
    if UserRepository.get_by_email(db, email):
        raise ConflictException("Email already registered")
    if UserRepository.get_by_username(db, data.username):
        raise ConflictException("Username already taken")
    issue_code(db, email)
    return {
        "message": "Verification code sent",
        "expires_in": settings.OTP_EXPIRE_MINUTES * 60,
        "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS,
    }


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create the account once the emailed code is correct, and sign the user in."""
    email = user_data.email.lower()
    consume_code(db, email, user_data.code)
    user = UserService.create(db, user_data.model_copy(update={"email": email}))
    return _token_for(user)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and get access token."""
    user = UserService.authenticate(db, credentials.email, credentials.password)
    return _token_for(user)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Email a one-time reset link. The response does not reveal whether the email exists."""
    request_password_reset(db, data.email)
    return {"message": "If an account exists for that email, we sent a reset link."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Set a new password from a reset link."""
    apply_password_reset(db, data.token, data.password)
    return {"message": "Password updated. You can sign in now."}


@router.get("/me", response_model=UserResponse)
def read_me(
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    """Get the currently authenticated user."""
    return UserService.get(db, request.get_user_id())


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    """Update the currently authenticated user."""
    return UserService.partial_update(db, request.get_user_id(), data)


@router.get("/{user_id}/profile", response_model=PublicUserResponse)
def read_profile(user_id: UUID, db: Session = Depends(get_db)):
    """Public profile of a user (no email or account flags)."""
    user = UserService.get(db, user_id)
    post_count = db.query(func.count(Post.id)).filter(Post.author_id == user.id).scalar() or 0
    return PublicUserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        created_at=user.created_at,
        post_count=post_count,
    )


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    if request.get_user_role() != "admin":  # match your role casing
        raise ForbiddenException("Admin only")
    return UserService.deactivate(db, user_id)


@router.post("/{user_id}/reactivate", response_model=UserResponse)
def reactivate_user(
    user_id: UUID,
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    if request.get_user_role() != UserRole.ADMIN.value:
        raise ForbiddenException("Admin only")
    return UserService.reactivate(db, user_id)


@router.get("/me/export.pdf")
def export_my_work(
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    user = UserService.get(db, request.get_user_id())
    posts = PostRepository.list_by_author(db, user.id)
    pdf = build_user_portfolio_pdf(user, posts)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="insidehub-{user.username}.pdf"'
        },
    )


@router.get("/{user_id}/export.pdf")
def export_user_work(
    user_id: UUID,
    request: RequestWrapper = Depends(get_request_wrapper),
    db: Session = Depends(get_db),
):
    if request.get_user_role() != UserRole.ADMIN.value:
        raise ForbiddenException("Admin only")
    user = UserService.get(db, user_id)
    posts = PostRepository.list_by_author(db, user.id)
    pdf = build_user_portfolio_pdf(user, posts)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="insidehub-{user.username}.pdf"'
        },
    )
