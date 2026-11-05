"""place names and order for post photos

Revision ID: 004
Revises: 003
Create Date: 2026-11-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("post_images", sa.Column("place_name", sa.String(length=200), nullable=True))
    op.add_column(
        "post_images",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("post_images", "position")
    op.drop_column("post_images", "place_name")
