"""Contract tests for the served web client (the static SPA).

The web UI is just another client of the same REST API. We can't unit-test the browser
DOM here, but we can cover the two things that actually break in practice:
  1. the server serves the app's files;
  2. `app.js` is valid JavaScript and only calls endpoints the API actually exposes
     (this catches client/server drift like a renamed route).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from server.api import create_app

STATIC = Path(__file__).resolve().parents[2] / "static"


def test_index_served_at_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "mealplan" in resp.text


def test_static_assets_served(client):
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "fetch(" in js.text  # it's the real client script

    css = client.get("/static/style.css")
    assert css.status_code == 200


def test_app_js_is_valid_javascript():
    node = shutil.which("node")
    if not node:  # pragma: no cover - environment without node
        pytest.skip("node not available to syntax-check app.js")
    result = subprocess.run([node, "--check", str(STATIC / "app.js")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_web_client_only_calls_existing_endpoints(tmp_path):
    """Every path app.js requests must match a real route on the app.

    Guards against the web UI and the API drifting apart (e.g. the search route move).
    """
    app = create_app(str(tmp_path / "web.db"))
    matchers = [
        re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", route.path) + "$")
        for route in app.routes
        if getattr(route, "path", None)
    ]

    js = (STATIC / "app.js").read_text()
    found: set[str] = set()
    for frag in re.findall(r"""[`"'](/[a-zA-Z][^`"']*)""", js):
        frag = frag.split("?")[0]                       # drop any query string
        frag = re.sub(r"\$\{[^}]+\}", "X", frag)         # template expr -> one path segment
        frag = frag.rstrip("/")
        if frag:
            found.add(frag)

    assert found, "no endpoint paths found in app.js"
    for path in sorted(found):
        assert any(m.match(path) for m in matchers), f"web UI calls an endpoint with no route: {path}"
