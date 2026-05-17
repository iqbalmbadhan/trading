"""create symbols and candles; TimescaleDB hypertable + rollups on Postgres

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 1m -> 5m -> 15m -> 1h -> 4h -> 1d continuous aggregates (Postgres only).
_AGGREGATES = [
    ("candles_5m", "5 minutes"),
    ("candles_15m", "15 minutes"),
    ("candles_1h", "1 hour"),
    ("candles_4h", "4 hours"),
    ("candles_1d", "1 day"),
]


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("base", sa.String(length=32), nullable=False),
        sa.Column("quote", sa.String(length=32), nullable=False),
        sa.Column("contract_type", sa.String(length=16), nullable=False, server_default="spot"),
        sa.Column("min_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tick_size", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("exchange", "symbol", name="uq_symbols_exchange_symbol"),
    )
    op.create_table(
        "candles",
        sa.Column(
            "symbol_id",
            sa.Integer(),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("timeframe", sa.String(length=8), primary_key=True),
        sa.Column("ts", sa.BigInteger(), primary_key=True),
        sa.Column("o", sa.Float(), nullable=False),
        sa.Column("h", sa.Float(), nullable=False),
        sa.Column("l", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=False),
        sa.Column("v", sa.Float(), nullable=False),
    )

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # TimescaleDB: hypertable on candles, partitioned by ts (epoch seconds).
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute(
        "SELECT create_hypertable('candles', 'ts', "
        "chunk_time_interval => 604800, if_not_exists => TRUE, migrate_data => TRUE)"
    )
    for view, bucket in _AGGREGATES:
        op.execute(f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {view}
            WITH (timescaledb.continuous) AS
            SELECT symbol_id,
                   time_bucket(extract(epoch FROM interval '{bucket}')::bigint, ts) AS bucket,
                   first(o, ts) AS o,
                   max(h) AS h,
                   min(l) AS l,
                   last(c, ts) AS c,
                   sum(v) AS v
            FROM candles
            WHERE timeframe = '1m'
            GROUP BY symbol_id, bucket
            WITH NO DATA
            """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for view, _ in reversed(_AGGREGATES):
            op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view}")
    op.drop_table("candles")
    op.drop_table("symbols")
