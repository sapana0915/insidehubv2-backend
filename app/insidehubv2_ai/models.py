import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.organizations.models import Organization
    from app.users.models import User


class AiPromptLog(Base):
    __tablename__ = "ai_prompt_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    used_web_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(200), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="ai_prompt_logs")
    organization: Mapped["Organization"] = relationship(back_populates="ai_prompt_logs")
