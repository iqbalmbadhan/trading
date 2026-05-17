"""Shared test fixtures: isolated async DB and HTTP client."""

import os
import tempfile

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create schema synchronously so no event loop is involved.
    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    testing_session = async_sessionmaker(async_engine, expire_on_commit=False)

    async def _override_get_db():
        async with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.test_db_path = path
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    os.unlink(path)


@pytest_asyncio.fixture()
async def db_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    testing_session = async_sessionmaker(async_engine, expire_on_commit=False)
    async with testing_session() as session:
        yield session
    await async_engine.dispose()
    os.unlink(path)
