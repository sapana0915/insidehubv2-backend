"""add organization email_domain

Revision ID: a1b2c3d4e5f6
Revises: fdafa12c7294
Create Date: 2026-11-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "fdafa12c7294"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("email_domain", sa.String(length=200), nullable=True),
    )
    op.create_index(
        op.f("ix_organizations_email_domain"),
        "organizations",
        ["email_domain"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_organizations_email_domain"), table_name="organizations")
    op.drop_column("organizations", "email_domain")
