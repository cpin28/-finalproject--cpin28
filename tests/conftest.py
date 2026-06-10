"""Shared fixtures.

The layering pays off here: `conn` gives unit/integration tests a real DB with no HTTP,
while `client` (FastAPI TestClient) and `api_client` (the real MealPlanClient driven over
an in-process ASGI transport) cover the contract and integration levels respectively.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from server.api import create_app
from server.db import connect, init_db
from mealplan_client import MealPlanClient


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def app(db_path):
    return create_app(db_path)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def live_server(app):
    """Run the real app under uvicorn in a background thread; yield its base URL."""
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):  # wait up to ~5s for startup
        if server.started:
            break
        time.sleep(0.05)
    else:  # pragma: no cover - startup failure
        raise RuntimeError("server did not start")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def api_client(live_server):
    """The real MealPlanClient driving the real server over a real socket."""
    c = MealPlanClient(live_server)
    yield c
    c.close()
