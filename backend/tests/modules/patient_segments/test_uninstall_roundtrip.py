"""patient_segments round-trip uninstall test.

Install → uninstall → reinstall must drop ONLY the module's tables
(``patient_segments``, ``patient_segment_links``) and leave every other
module untouched. The branch-scoped downgrade target is
``patient_segments@base`` (full branch uninstall). Marked
``alembic_roundtrip`` and excluded from the default pytest run.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest

from app.config import settings

pytestmark = pytest.mark.alembic_roundtrip

BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"

PSEG_TABLES = {"patient_segments", "patient_segment_links"}


def _alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args],
        cwd=BACKEND_ROOT,
        check=True,
    )


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _list_tables_async() -> set[str]:
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name != 'alembic_version'"
        )
        return {row["table_name"] for row in rows}
    finally:
        await conn.close()


def _list_tables() -> set[str]:
    return asyncio.run(_list_tables_async())


def test_patient_segments_uninstall_roundtrip_is_branch_scoped() -> None:
    _alembic("upgrade", "heads")
    before = _list_tables()
    assert PSEG_TABLES.issubset(before), "segment tables missing after upgrade"

    # Branch-scoped form (<label>@-N): plain <label>@base would downgrade
    # every branch to the shared ancestor (see _downgrade_target_for).
    _alembic("downgrade", "patient_segments@-1")
    after_down = _list_tables()
    assert PSEG_TABLES.isdisjoint(after_down), "segment tables still present after downgrade"

    other_tables = before - PSEG_TABLES
    assert other_tables.issubset(after_down), "downgrade leaked beyond patient_segments branch"

    _alembic("upgrade", "heads")
    after_up = _list_tables()
    assert PSEG_TABLES.issubset(after_up), "segment tables missing after re-upgrade"
    assert before == after_up, "round-trip left schema in a different state"
