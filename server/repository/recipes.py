"""SQL for recipes and their ingredient lines."""

from __future__ import annotations

import sqlite3

from .. import schemas


def _recipe_ingredients(conn: sqlite3.Connection, recipe_id: int) -> list[schemas.RecipeIngredient]:
    rows = conn.execute(
        """
        SELECT ri.ingredient_id, i.name, ri.quantity, ri.unit
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY i.name
        """,
        (recipe_id,),
    ).fetchall()
    return [schemas.RecipeIngredient(**dict(r)) for r in rows]


def create_recipe(conn: sqlite3.Connection, data: schemas.RecipeCreate) -> schemas.Recipe:
    cur = conn.execute(
        """INSERT INTO recipes (name, description, instructions, servings, prep_time_minutes)
           VALUES (?, ?, ?, ?, ?)""",
        (data.name, data.description, data.instructions, data.servings, data.prep_time_minutes),
    )
    recipe_id = cur.lastrowid
    for ri in data.ingredients:
        conn.execute(
            "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
            (recipe_id, ri.ingredient_id, ri.quantity, ri.unit),
        )
    conn.commit()
    return get_recipe(conn, recipe_id)  # type: ignore[return-value]


def get_recipe(conn: sqlite3.Connection, recipe_id: int) -> schemas.Recipe | None:
    r = conn.execute(
        """SELECT id, name, description, instructions, servings, prep_time_minutes
           FROM recipes WHERE id = ?""",
        (recipe_id,),
    ).fetchone()
    if not r:
        return None
    return schemas.Recipe(**dict(r), ingredients=_recipe_ingredients(conn, recipe_id))


def list_recipes(conn: sqlite3.Connection, query: str | None = None) -> list[schemas.Recipe]:
    if query:
        rows = conn.execute(
            "SELECT id FROM recipes WHERE name LIKE ? ORDER BY name",
            (f"%{query}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT id FROM recipes ORDER BY name").fetchall()
    return [get_recipe(conn, r["id"]) for r in rows]  # type: ignore[misc]


def delete_recipe(conn: sqlite3.Connection, recipe_id: int) -> bool:
    cur = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    return cur.rowcount > 0


def recipes_by_id(conn: sqlite3.Connection, ids: set[int]) -> dict[int, schemas.Recipe]:
    return {i: r for i in ids if (r := get_recipe(conn, i)) is not None}
