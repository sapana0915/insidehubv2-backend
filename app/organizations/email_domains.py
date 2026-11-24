"""Normalize and validate organization email domains for auto-join."""

from app.core.exceptions import ValidationException

# Consumer / free-mail domains cannot be claimed for auto-join.
BLOCKED_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.in",
        "yahoo.co.uk",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "msn.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "gmx.com",
        "gmx.net",
        "mail.com",
        "yandex.com",
        "yandex.ru",
        "zoho.com",
        "qq.com",
        "163.com",
        "126.com",
    }
)


def normalize_email_domain(value: str | None) -> str | None:
    if value is None:
        return None
    domain = value.strip().lower()
    if domain.startswith("@"):
        domain = domain[1:]
    domain = domain.rstrip(".")
    if not domain:
        return None
    if " " in domain or "/" in domain or ":" in domain:
        raise ValidationException("Email domain looks invalid")
    if "." not in domain:
        raise ValidationException("Email domain must include a dot (e.g. company.com)")
    if domain in BLOCKED_EMAIL_DOMAINS:
        raise ValidationException(
            f"'{domain}' is a public email provider and cannot be used for organization auto-join"
        )
    return domain


def domain_from_email(email: str) -> str | None:
    email = email.strip().lower()
    if "@" not in email:
        return None
    _, _, domain = email.partition("@")
    domain = domain.strip().rstrip(".")
    return domain or None
