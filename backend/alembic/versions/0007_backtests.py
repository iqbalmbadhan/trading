"""create backtests

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "strategy_id",
            sa.Integer(),
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("start_ts", sa.BigInteger(), nullable=True),
        sa.Column("end_ts", sa.BigInteger(), nullable=True),
        sa.Column("starting_cash", sa.Float(), nullable=False, server_default="10000"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("monte_carlo", sa.JSON(), nullable=False),
        sa.Column("equity_curve", sa.JSON(), nullable=False),
        sa.Column("trade_pnls", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_backtests_user_id", "backtests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_backtests_user_id", table_name="backtests")
    op.drop_table("backtests")
