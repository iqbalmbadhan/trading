"""Rotate the master key: re-wrap every stored data key, no plaintext exposure.

Usage: OLD_MASTER_KEY=... NEW_MASTER_KEY=... python -m app.scripts.rotate_master_key

Only the small per-secret encrypted DEKs are re-encrypted; the ciphertexts
are untouched. After a successful run, set MASTER_KEY to the new value and
restart the services.
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.core.crypto import rewrap_dek
from app.db.models import ExchangeAccount
from app.db.session import SessionLocal


async def _main(old_key: str, new_key: str) -> None:
    rotated = 0
    async with SessionLocal() as session:
        accounts = (await session.execute(select(ExchangeAccount))).scalars().all()
        for acc in accounts:
            acc.encrypted_api_key_dek = rewrap_dek(old_key, new_key, acc.encrypted_api_key_dek)
            acc.encrypted_secret_dek = rewrap_dek(old_key, new_key, acc.encrypted_secret_dek)
            rotated += 1
        await session.commit()
    print(f"re-wrapped DEKs for {rotated} exchange account(s)")
    print("Now set MASTER_KEY to the new value and restart all services.")


if __name__ == "__main__":
    old = os.environ.get("OLD_MASTER_KEY")
    new = os.environ.get("NEW_MASTER_KEY")
    if not old or not new:
        print("set OLD_MASTER_KEY and NEW_MASTER_KEY environment variables")
        raise SystemExit(2)
    asyncio.run(_main(old, new))
