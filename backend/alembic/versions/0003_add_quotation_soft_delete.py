"""Add soft-delete fields to quotations

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("quotations")}

    if "is_deleted" not in columns:
        op.add_column(
            "quotations",
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if "deleted_at" not in columns:
        op.add_column("quotations", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    if "deleted_by" not in columns:
        op.add_column("quotations", sa.Column("deleted_by", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("quotations")}

    if "deleted_by" in columns:
        op.drop_column("quotations", "deleted_by")
    if "deleted_at" in columns:
        op.drop_column("quotations", "deleted_at")
    if "is_deleted" in columns:
        op.drop_column("quotations", "is_deleted")
