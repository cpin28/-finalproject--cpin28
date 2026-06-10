"""SQL for the canonical ingredient list."""

from __future__ import annotations

import sqlite3

from .. import schemas


def create_ingredient(conn: sqlite3.Connection, data: schemas.IngredientCreate) -> schemas.Ingredient:
    cur = conn.execute(
        "INSERT INTO ingredients (name, default_unit) VALUES (?, ?)",
        (data.name, data.default_unit),
    )
    conn.commit()
    return schemas.Ingredient(id=cur.lastrowid, name=data.name, default_unit=data.default_unit)


def list_ingredients(conn: sqlite3.Connection) -> list[schemas.Ingredient]:
    rows = conn.execute("SELECT id, name, default_unit FROM ingredients ORDER BY name").fetchall()
    return [schemas.Ingredient(**dict(r)) for r in rows]


def get_ingredient(conn: sqlite3.Connection, ingredient_id: int) -> schemas.Ingredient | None:
    r = conn.execute(
        "SELECT id, name, default_unit FROM ingredients WHERE id = ?", (ingredient_id,)
    ).fetchone()
    return schemas.Ingredient(**dict(r)) if r else None
