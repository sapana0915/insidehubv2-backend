import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_email, verification_email
from app.core.exceptions import DetailedException, ValidationException
from .models import EmailVerification


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hash_code(code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _latest_open(db: Session, email: str) -> EmailVerification | None:
    return (
        db.query(EmailVerification)
        .filter(EmailVerification.email == email, EmailVerification.consumed_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
        .first()
    )


def issue_code(db: Session, email: str) -> None:
    """Create a 6-digit code for an email and send it. Plain codes are never stored."""
    email = email.strip().lower()
    latest = _latest_open(db, email)
    if latest is not None:
        elapsed = (_now() - _aware(latest.created_at)).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed) or 1
            raise DetailedException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {wait} seconds before requesting another code",
            )
        latest.consumed_at = _now()

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        EmailVerification(
            email=email,
            code_hash=_hash_code(code),
            expires_at=_now() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
            attempts=0,
        )
    )
    db.commit()

    subject, text, html = verification_email(code)
    send_email(email, subject, text, html)


def consume_code(db: Session, email: str, code: str) -> None:
    """Check a code and mark it used. Raises ValidationException when it fails."""
    email = email.strip().lower()
    row = _latest_open(db, email)
    if row is None:
        raise ValidationException("Request a code first")
    if _aware(row.expires_at) < _now():
        raise ValidationException("Code expired, request a new one")
    if row.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise ValidationException("Too many attempts, request a new one")
    if not hmac.compare_digest(row.code_hash, _hash_code(code.strip())):
        row.attempts += 1
        db.commit()
        raise ValidationException("Invalid code")
    row.consumed_at = _now()
    db.commit()
