import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.insidehubv2_ai.models import AiPromptLog
    from app.users.models import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_domain: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        unique=True,
        index=True,
    )

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
        foreign_keys="User.organization_id",
    )
    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )
    ai_prompt_logs: Mapped[list["AiPromptLog"]] = relationship(
        back_populates="organization",
    )
