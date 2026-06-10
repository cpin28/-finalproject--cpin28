"""Seed a database with simple, beginner-friendly recipes, a pantry, a plan, and a few
ingredient substitutions.

Run: `python -m migrations.seed [db_path]`  (defaults to $MEALPLAN_DB or mealplan.db)

Idempotent enough for a demo: it skips seeding if any recipes already exist. The pantry is
chosen to show the feature off — it has oil but no butter, so butter-using recipes come up
as "makeable with a substitution".
"""

from __future__ import annotations

import os
import sys

from server import repository, schemas
from server.db import connect, init_db

INGREDIENTS = [
    ("flour", "g"), ("egg", "unit"), ("milk", "ml"), ("butter", "g"), ("sugar", "g"),
    ("pasta", "g"), ("tomato", "unit"), ("onion", "unit"), ("chicken breast", "g"),
    ("rice", "g"), ("oil", "ml"), ("yogurt", "ml"), ("honey", "g"), ("water", "ml"),
]

# (name, difficulty, servings, prep_minutes, [(ingredient_name, qty, unit), ...])
RECIPES = [
    ("Scrambled Eggs", "beginner", 2, 10, [("egg", 4, "unit"), ("butter", 15, "g"), ("milk", 30, "ml")]),
    ("Pancakes", "beginner", 4, 20, [("flour", 200, "g"), ("egg", 2, "unit"), ("milk", 300, "ml"), ("butter", 30, "g"), ("sugar", 20, "g")]),
    ("Tomato Pasta", "easy", 2, 25, [("pasta", 200, "g"), ("tomato", 3, "unit"), ("onion", 1, "unit"), ("oil", 15, "ml")]),
    ("Chicken & Rice", "intermediate", 2, 35, [("chicken breast", 300, "g"), ("rice", 150, "g"), ("onion", 1, "unit"), ("oil", 15, "ml")]),
]

# (ingredient_name, substitute_name, ratio, note) — directional
SUBSTITUTIONS = [
    ("butter", "oil", 0.75, "use about 3/4 as much oil"),
    ("oil", "butter", 1.33, "use a bit more, melted"),
    ("milk", "yogurt", 1.0, "thin with a splash of water"),
    ("milk", "water", 1.0, "lighter and less rich"),
    ("sugar", "honey", 0.75, "use 3/4 and cut other liquids a little"),
    ("honey", "sugar", 1.33, "add a splash of water"),
]

# has oil (not butter) so butter recipes are "makeable with a substitution"
PANTRY = [("flour", 1000, "g"), ("egg", 6, "unit"), ("milk", 500, "ml"), ("oil", 250, "ml"), ("rice", 500, "g")]

PLAN = [
    ("2026-06-10", "breakfast", "Scrambled Eggs"),
    ("2026-06-10", "dinner", "Tomato Pasta"),
    ("2026-06-11", "dinner", "Chicken & Rice"),
]


def seed(db_path: str) -> None:
    conn = connect(db_path)
    init_db(conn)
    if repository.list_recipes(conn):
        print(f"{db_path} already has recipes — skipping seed.")
        conn.close()
        return

    ids: dict[str, int] = {}
    for name, unit in INGREDIENTS:
        ids[name] = repository.create_ingredient(conn, schemas.IngredientCreate(name=name, default_unit=unit)).id

    recipe_ids: dict[str, int] = {}
    for name, difficulty, servings, prep, items in RECIPES:
        recipe = repository.create_recipe(conn, schemas.RecipeCreate(
            name=name, difficulty=difficulty, servings=servings, prep_time_minutes=prep,
            ingredients=[schemas.RecipeIngredientInput(ingredient_id=ids[n], quantity=q, unit=u) for n, q, u in items],
        ))
        recipe_ids[name] = recipe.id

    for ingredient, substitute, ratio, note in SUBSTITUTIONS:
        repository.create_substitution(conn, schemas.SubstitutionInput(
            ingredient_id=ids[ingredient], substitute_id=ids[substitute], ratio=ratio, note=note,
        ))

    for name, qty, unit in PANTRY:
        repository.set_pantry_item(conn, schemas.PantryItemInput(ingredient_id=ids[name], quantity=qty, unit=unit))

    for date, meal_type, recipe_name in PLAN:
        repository.create_planned_meal(conn, schemas.PlannedMealCreate(
            date=date, meal_type=meal_type, recipe_id=recipe_ids[recipe_name],
        ))

    conn.close()
    print(f"Seeded {db_path}: {len(INGREDIENTS)} ingredients, {len(RECIPES)} recipes, "
          f"{len(SUBSTITUTIONS)} substitutions, {len(PLAN)} planned meals.")


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MEALPLAN_DB", "mealplan.db")
    seed(db_path)


if __name__ == "__main__":
    main()
