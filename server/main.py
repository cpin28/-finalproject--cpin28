"""Server entry point: `mealplan-server` (or `python -m server.main`)."""

from __future__ import annotations

import os

import uvicorn

from .api import create_app


def main() -> None:
    db_path = os.environ.get("MEALPLAN_DB", "mealplan.db")
    host = os.environ.get("MEALPLAN_HOST", "127.0.0.1")
    port = int(os.environ.get("MEALPLAN_PORT", "8000"))
    uvicorn.run(create_app(db_path), host=host, port=port)


if __name__ == "__main__":
    main()
