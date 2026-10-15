"""Verifica la migración contra un PostgreSQL real (en CI o con docker compose)."""

import os
import subprocess
import sys

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL no definida"),
]


def _alembic(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "alembic", *args], check=True)


def _diff(connection: Connection) -> list[object]:
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return list(compare_metadata(context, Base.metadata))


def _tables(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names()) - {"alembic_version"}


async def test_upgrade_matches_models_and_downgrade_cleans_up() -> None:
    assert DATABASE_URL
    engine = create_async_engine(DATABASE_URL)
    try:
        _alembic("downgrade", "base")
        _alembic("upgrade", "head")
        async with engine.connect() as conn:
            assert await conn.run_sync(_tables) == set(Base.metadata.tables)
            assert await conn.run_sync(_diff) == []

        _alembic("downgrade", "base")
        async with engine.connect() as conn:
            assert await conn.run_sync(_tables) == set()
        _alembic("upgrade", "head")
    finally:
        await engine.dispose()
