"""Integration: repository against a real SQLite database (temp file).

Exercises the actual SQL — joins, the pantry upsert, the foreign-key cascade — that the
unit tests deliberately skip.
"""

from __future__ import annotations

from server import repository, schemas


def test_recipe_persists_with_joined_ingredient_names(conn):
    flour = repository.create_ingredient(conn, schemas.IngredientCreate(name="flour", default_unit="g"))
    recipe = repository.create_recipe(conn, schemas.RecipeCreate(
        name="Bread", servings=2,
        ingredients=[schemas.RecipeIngredientInput(ingredient_id=flour.id, quantity=500, unit="g")],
    ))
    fetched = repository.get_recipe(conn, recipe.id)
    assert fetched.name == "Bread"
    assert fetched.ingredients[0].name == "flour"


def test_pantry_upsert_replaces_quantity(conn):
    egg = repository.create_ingredient(conn, schemas.IngredientCreate(name="egg"))
    repository.set_pantry_item(conn, schemas.PantryItemInput(ingredient_id=egg.id, quantity=6, unit="unit"))
    repository.set_pantry_item(conn, schemas.PantryItemInput(ingredient_id=egg.id, quantity=12, unit="unit"))
    pantry = repository.list_pantry(conn)
    assert len(pantry) == 1 and pantry[0].quantity == 12


def test_delete_recipe_cascades_ingredients(conn):
    flour = repository.create_ingredient(conn, schemas.IngredientCreate(name="flour", default_unit="g"))
    recipe = repository.create_recipe(conn, schemas.RecipeCreate(
        name="Bread", servings=1,
        ingredients=[schemas.RecipeIngredientInput(ingredient_id=flour.id, quantity=500, unit="g")],
    ))
    assert repository.delete_recipe(conn, recipe.id) is True
    assert repository.get_recipe(conn, recipe.id) is None
    rows = conn.execute("SELECT COUNT(*) AS n FROM recipe_ingredients").fetchone()["n"]
    assert rows == 0


def test_planned_meals_filtered_by_date_range(conn):
    r = repository.create_recipe(conn, schemas.RecipeCreate(name="Soup", servings=2))
    for date in ("2026-06-09", "2026-06-10", "2026-06-15"):
        repository.create_planned_meal(conn, schemas.PlannedMealCreate(date=date, meal_type="dinner", recipe_id=r.id))
    week = repository.list_planned_meals(conn, start="2026-06-10", end="2026-06-14")
    assert [m.date for m in week] == ["2026-06-10"]
