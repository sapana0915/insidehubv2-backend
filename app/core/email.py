import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.exceptions import DetailedException

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Deliver an email. The console backend prints it to the logs instead."""
    if settings.EMAIL_BACKEND == "console":
        logger.warning("[EMAIL] To: %s | %s | %s", to, subject, text.replace("\n", " "))
        return

    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        raise DetailedException(502, "Email is not configured. Set the SMTP values in .env.")

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        raise DetailedException(502, "Couldn't send the code. Please try again.") from exc


def verification_email(code: str) -> tuple[str, str, str]:
    """Subject, plain text and HTML for a sign-up code."""
    minutes = settings.OTP_EXPIRE_MINUTES
    subject = f"{code} is your InsideHub code"
    text = (
        f"Your InsideHub verification code is {code}.\n"
        f"It expires in {minutes} minutes. If you didn't ask for it, ignore this email."
    )
    html = f"""
    <div style="background:#f5efe4;padding:32px;font-family:Georgia,serif;color:#1f1b16">
      <h1 style="font-style:italic;margin:0">Inside<span style="color:#c65d3b">Hub</span></h1>
      <p style="letter-spacing:.2em;font-size:12px;text-transform:uppercase">Field journal</p>
      <p>Your verification code:</p>
      <p style="font-family:monospace;font-size:32px;letter-spacing:.4em;margin:8px 0">{code}</p>
      <p style="color:#5b5247">It expires in {minutes} minutes.</p>
    </div>
    """
    return subject, text, html
