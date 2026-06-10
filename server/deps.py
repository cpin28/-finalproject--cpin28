"""Shared FastAPI dependencies.

Extracted from `api.py` so the per-resource routers can import the connection
dependency without depending on the app module (which would be a circular import).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Request

from .db import connect


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection per request, scoped to the app's db_path."""
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
