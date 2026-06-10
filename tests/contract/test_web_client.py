"""Contract tests for the served web client (the static SPA).

The web UI is just another client of the same REST API, but the *server* is responsible
for serving its files — so we assert those routes exist and return the right thing.
"""

from __future__ import annotations


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
