"""create risk_rules and kill_switch_events

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_type", sa.String(length=32), nullable=False, server_default="global"),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_risk_rules_user_id", "risk_rules", ["user_id"])

    op.create_table(
        "kill_switch_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_kill_switch_events_user_id", "kill_switch_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_kill_switch_events_user_id", table_name="kill_switch_events")
    op.drop_table("kill_switch_events")
    op.drop_index("ix_risk_rules_user_id", table_name="risk_rules")
    op.drop_table("risk_rules")
