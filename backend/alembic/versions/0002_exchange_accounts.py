"""create exchange_accounts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exchange_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("encrypted_api_key_dek", sa.String(length=512), nullable=False),
        sa.Column("encrypted_api_key", sa.String(length=1024), nullable=False),
        sa.Column("encrypted_secret_dek", sa.String(length=512), nullable=False),
        sa.Column("encrypted_secret", sa.String(length=1024), nullable=False),
        sa.Column(
            "permissions_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_exchange_accounts_user_id", "exchange_accounts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_exchange_accounts_user_id", table_name="exchange_accounts")
    op.drop_table("exchange_accounts")
