"""Data access layer: every SQL statement lives here, nothing else touches the DB.

Functions take a `sqlite3.Connection` and return plain `schemas` objects, so callers
(the API routes, tests) never see raw rows. This is the repository pattern — it's what
lets the unit tests exercise `planner` with no database at all.
"""

from __future__ import annotations

import sqlite3

from . import schemas


# --- Ingredients ---------------------------------------------------------

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


# --- Recipes -------------------------------------------------------------

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


# --- Pantry --------------------------------------------------------------

def set_pantry_item(conn: sqlite3.Connection, data: schemas.PantryItemInput) -> schemas.PantryItem:
    conn.execute(
        """INSERT INTO pantry_items (ingredient_id, quantity, unit) VALUES (?, ?, ?)
           ON CONFLICT(ingredient_id) DO UPDATE SET quantity = excluded.quantity, unit = excluded.unit""",
        (data.ingredient_id, data.quantity, data.unit),
    )
    conn.commit()
    name = conn.execute("SELECT name FROM ingredients WHERE id = ?", (data.ingredient_id,)).fetchone()["name"]
    return schemas.PantryItem(ingredient_id=data.ingredient_id, name=name, quantity=data.quantity, unit=data.unit)


def list_pantry(conn: sqlite3.Connection) -> list[schemas.PantryItem]:
    rows = conn.execute(
        """SELECT p.ingredient_id, i.name, p.quantity, p.unit
           FROM pantry_items p JOIN ingredients i ON i.id = p.ingredient_id
           ORDER BY i.name""",
    ).fetchall()
    return [schemas.PantryItem(**dict(r)) for r in rows]


def remove_pantry_item(conn: sqlite3.Connection, ingredient_id: int) -> bool:
    cur = conn.execute("DELETE FROM pantry_items WHERE ingredient_id = ?", (ingredient_id,))
    conn.commit()
    return cur.rowcount > 0


# --- Meal plan -----------------------------------------------------------

def create_planned_meal(conn: sqlite3.Connection, data: schemas.PlannedMealCreate) -> schemas.PlannedMeal | None:
    recipe = get_recipe(conn, data.recipe_id)
    if recipe is None:
        return None
    servings = data.servings or recipe.servings
    cur = conn.execute(
        "INSERT INTO planned_meals (date, meal_type, recipe_id, servings) VALUES (?, ?, ?, ?)",
        (data.date, data.meal_type, data.recipe_id, servings),
    )
    conn.commit()
    return schemas.PlannedMeal(
        id=cur.lastrowid, date=data.date, meal_type=data.meal_type,
        recipe_id=data.recipe_id, recipe_name=recipe.name, servings=servings,
    )


def list_planned_meals(
    conn: sqlite3.Connection, start: str | None = None, end: str | None = None
) -> list[schemas.PlannedMeal]:
    sql = """SELECT pm.id, pm.date, pm.meal_type, pm.recipe_id, r.name AS recipe_name, pm.servings
             FROM planned_meals pm JOIN recipes r ON r.id = pm.recipe_id"""
    clauses, params = [], []
    if start:
        clauses.append("pm.date >= ?")
        params.append(start)
    if end:
        clauses.append("pm.date <= ?")
        params.append(end)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY pm.date, pm.meal_type"
    rows = conn.execute(sql, params).fetchall()
    return [schemas.PlannedMeal(**dict(r)) for r in rows]


def delete_planned_meal(conn: sqlite3.Connection, meal_id: int) -> bool:
    cur = conn.execute("DELETE FROM planned_meals WHERE id = ?", (meal_id,))
    conn.commit()
    return cur.rowcount > 0
