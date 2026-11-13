import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import password_reset_email, send_email
from app.core.exceptions import DetailedException, ValidationException
from app.core.security import hash_password
from .models import PasswordReset, User
from .repositories import UserRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hash_token(token: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def _latest_open(db: Session, user_id) -> PasswordReset | None:
    return (
        db.query(PasswordReset)
        .filter(PasswordReset.user_id == user_id, PasswordReset.consumed_at.is_(None))
        .order_by(PasswordReset.created_at.desc())
        .first()
    )


def request_password_reset(db: Session, email: str) -> None:
    """Email a reset link when the account exists. Callers always return the same message."""
    user = UserRepository.get_by_email(db, email.strip().lower())
    if user is None or not user.is_active:
        return

    latest = _latest_open(db, user.id)
    if latest is not None:
        elapsed = (_now() - _aware(latest.created_at)).total_seconds()
        if elapsed < settings.PASSWORD_RESET_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.PASSWORD_RESET_RESEND_COOLDOWN_SECONDS - elapsed) or 1
            raise DetailedException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {wait} seconds before requesting another link",
            )
        latest.consumed_at = _now()

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=_now() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
    )
    db.commit()

    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    subject, text, html = password_reset_email(link)
    send_email(user.email, subject, text, html)


def apply_password_reset(db: Session, token: str, password: str) -> None:
    """Set a new password and consume the token."""
    row = (
        db.query(PasswordReset)
        .filter(PasswordReset.token_hash == _hash_token(token.strip()), PasswordReset.consumed_at.is_(None))
        .first()
    )
    if row is None or _aware(row.expires_at) < _now():
        raise ValidationException("This reset link is invalid or expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None or not user.is_active:
        raise ValidationException("This reset link is invalid or expired")

    user.hashed_password = hash_password(password)
    row.consumed_at = _now()
    db.commit()
