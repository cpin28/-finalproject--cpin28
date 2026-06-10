"""Application assembly — wires the per-resource routers into one FastAPI app.

Routes themselves live in `server/routers/` (one module per resource). This module
just builds the app: opens/initialises the database, includes the routers, and serves
the static web client. Keeping assembly separate from the routes is what lets each
resource's routes stay small and independently navigable.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import connect, init_db
from .routers import ingredients, pantry, plan, recipes, shopping

DEFAULT_DB = os.environ.get("MEALPLAN_DB", "mealplan.db")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(db_path: str = DEFAULT_DB) -> FastAPI:
    app = FastAPI(title="mealplan", version="0.1.0")
    app.state.db_path = db_path

    boot = connect(db_path)
    init_db(boot)
    boot.close()

    for module in (ingredients, recipes, pantry, plan, shopping):
        app.include_router(module.router)

    # Serve the static single-page web client.
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(STATIC_DIR / "index.html")

    return app
