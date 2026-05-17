"""Create (or update) an admin user.

Usage: python -m app.scripts.create_admin <email> <password>
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


async def _main(email: str, password: str) -> None:
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    role="admin",
                )
            )
            action = "created"
        else:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            action = "updated"
        await session.commit()
    print(f"admin {action}: {email}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m app.scripts.create_admin <email> <password>")
        raise SystemExit(2)
    asyncio.run(_main(sys.argv[1], sys.argv[2]))
