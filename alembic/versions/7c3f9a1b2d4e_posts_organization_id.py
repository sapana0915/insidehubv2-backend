"""posts organization_id for tenant scoping

Revision ID: 7c3f9a1b2d4e
Revises: 4a2a8e96ba37
Create Date: 2026-11-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c3f9a1b2d4e"
down_revision: Union[str, None] = "4a2a8e96ba37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_posts_organization_id"), "posts", ["organization_id"], unique=False)

    # Backfill from the author's organization.
    op.execute(
        """
        UPDATE posts
        SET organization_id = users.organization_id
        FROM users
        WHERE posts.author_id = users.id
          AND users.organization_id IS NOT NULL
        """
    )
    # Posts whose authors have no org cannot be scoped — remove them.
    op.execute("DELETE FROM posts WHERE organization_id IS NULL")

    op.alter_column("posts", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_posts_organization_id_organizations",
        "posts",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_posts_organization_id_organizations", "posts", type_="foreignkey")
    op.drop_index(op.f("ix_posts_organization_id"), table_name="posts")
    op.drop_column("posts", "organization_id")
