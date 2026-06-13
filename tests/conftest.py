"""Shared pytest fixtures for sample-librarian tests.

Provides:
- ``db_conn`` — an initialised SQLite connection (auto-closed after test)
- ``sample_factory`` — callable that inserts test samples and returns sample dicts
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure the project root is importable so ``import librarian.db`` works.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from librarian.db import get_db, init_db, upsert_sample  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_conn(tmp_path: Path) -> Any:
    """Return an initialised sqlite3.Connection backed by a temp DB file.

    The connection is closed automatically after the test finishes.
    """
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = get_db(db_path)
    yield conn
    conn.close()


@pytest.fixture()
def sample_factory():
    """Return a function that inserts a test sample into *conn*.

    Usage::

        sid = sample_factory(conn, name="808 Kick", category="Kick", tags=["punchy"])
    """

    def _make(
        conn,
        *,
        name: str = "Test Sample",
        category: str = "",
        path: str | None = None,
        ext: str = "wav",
        size: int = 1024,
        folder: str = "/test/folder",
        root: str = "/test",
        file_hash: str | None = None,
        strings: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> int:
        record: dict[str, Any] = {
            "path": path or f"/test/{name.replace(' ', '_').lower()}.{ext}",
            "name": name,
            "ext": ext,
            "size": size,
            "category": category,
            "folder": folder,
            "root": root,
            "file_hash": file_hash,
            "strings": strings or [],
            "tags": tags or [],
        }
        return upsert_sample(conn, record)

    return _make
