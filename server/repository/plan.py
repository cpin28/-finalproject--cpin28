"""SQL for the weekly meal plan.

Depends on `recipes.get_recipe` to resolve and validate a recipe when scheduling a meal
— the one cross-entity reference in this package, made explicit by the import.
"""

from __future__ import annotations

import sqlite3

from .. import schemas
from .recipes import get_recipe


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
