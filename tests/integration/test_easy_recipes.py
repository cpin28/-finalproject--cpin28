"""The 100-easy-recipe loader: it populates a database and is safe to re-run.

Guards the shipped catalogue (every recipe tagged "easy", every ingredient given a unit)
and the loader's idempotency, so re-running it — or running it after seed.py — never
duplicates rows.
"""

from __future__ import annotations

from migrations.easy_recipes import RECIPES, UNITS, load
from server import repository
from server.db import connect, init_db


def test_catalogue_is_100_easy_recipes_with_known_units():
    assert len(RECIPES) == 100
    assert len({name for name, *_ in RECIPES}) == 100  # names are unique
    referenced = {ing for _, _, _, items in RECIPES for ing, _ in items}
    assert referenced <= UNITS.keys()  # every ingredient has a declared unit


def test_load_populates_and_tags_easy(db_path):
    assert load(db_path) == 100
    conn = connect(db_path)
    init_db(conn)
    recipes = repository.list_recipes(conn)
    assert len(recipes) == 100
    assert all(r.difficulty == "easy" for r in recipes)
    assert all(r.ingredients for r in recipes)  # none came out empty
    assert client_filter_easy(conn) == 100
    conn.close()


def client_filter_easy(conn) -> int:
    return len(repository.list_recipes(conn, difficulty="easy"))


def test_load_is_idempotent(db_path):
    assert load(db_path) == 100
    assert load(db_path) == 0  # second run adds nothing
    conn = connect(db_path)
    init_db(conn)
    assert len(repository.list_recipes(conn)) == 100
    assert len(repository.list_ingredients(conn)) == 93  # ingredients reused, not duplicated
    conn.close()
