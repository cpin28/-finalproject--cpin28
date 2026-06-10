"""REST API — the single entry point clients talk to.

Routes are thin: they validate input via `schemas`, delegate to `repository` for
storage and `planner` for derived data, and return `schemas` objects. No SQL and no
business logic live here.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import planner, repository, schemas
from .db import connect, init_db

DEFAULT_DB = os.environ.get("MEALPLAN_DB", "mealplan.db")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def create_app(db_path: str = DEFAULT_DB) -> FastAPI:
    app = FastAPI(title="mealplan", version="0.1.0")
    app.state.db_path = db_path

    boot = connect(db_path)
    init_db(boot)
    boot.close()

    # --- Ingredients ---
    @app.get("/ingredients", response_model=list[schemas.Ingredient])
    def list_ingredients(conn: sqlite3.Connection = Depends(get_conn)):
        return repository.list_ingredients(conn)

    @app.post("/ingredients", response_model=schemas.Ingredient, status_code=201)
    def create_ingredient(data: schemas.IngredientCreate, conn: sqlite3.Connection = Depends(get_conn)):
        try:
            return repository.create_ingredient(conn, data)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="ingredient name already exists")

    # --- Recipes ---
    @app.get("/recipes", response_model=list[schemas.Recipe])
    def list_recipes(q: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
        return repository.list_recipes(conn, q)

    @app.post("/recipes", response_model=schemas.Recipe, status_code=201)
    def create_recipe(data: schemas.RecipeCreate, conn: sqlite3.Connection = Depends(get_conn)):
        return repository.create_recipe(conn, data)

    @app.get("/recipes/{recipe_id}", response_model=schemas.Recipe)
    def get_recipe(recipe_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        recipe = repository.get_recipe(conn, recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="recipe not found")
        return recipe

    @app.delete("/recipes/{recipe_id}", status_code=204)
    def delete_recipe(recipe_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        if not repository.delete_recipe(conn, recipe_id):
            raise HTTPException(status_code=404, detail="recipe not found")

    @app.get("/recipes/{recipe_id}/can-make", response_model=schemas.CookCheck)
    def can_make(recipe_id: int, servings: int | None = None, conn: sqlite3.Connection = Depends(get_conn)):
        recipe = repository.get_recipe(conn, recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="recipe not found")
        pantry = repository.list_pantry(conn)
        missing = planner.missing_for_recipe(recipe, pantry, servings)
        return schemas.CookCheck(recipe_id=recipe_id, can_make=not missing, missing=missing)

    # --- Pantry ---
    @app.get("/pantry", response_model=list[schemas.PantryItem])
    def list_pantry(conn: sqlite3.Connection = Depends(get_conn)):
        return repository.list_pantry(conn)

    @app.put("/pantry", response_model=schemas.PantryItem)
    def set_pantry(data: schemas.PantryItemInput, conn: sqlite3.Connection = Depends(get_conn)):
        if repository.get_ingredient(conn, data.ingredient_id) is None:
            raise HTTPException(status_code=404, detail="ingredient not found")
        return repository.set_pantry_item(conn, data)

    @app.delete("/pantry/{ingredient_id}", status_code=204)
    def remove_pantry(ingredient_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        if not repository.remove_pantry_item(conn, ingredient_id):
            raise HTTPException(status_code=404, detail="pantry item not found")

    # --- Meal plan ---
    @app.get("/plan", response_model=list[schemas.PlannedMeal])
    def list_plan(start: str | None = None, end: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
        return repository.list_planned_meals(conn, start, end)

    @app.post("/plan", response_model=schemas.PlannedMeal, status_code=201)
    def add_plan(data: schemas.PlannedMealCreate, conn: sqlite3.Connection = Depends(get_conn)):
        if data.meal_type not in schemas.MEAL_TYPES:
            raise HTTPException(status_code=422, detail=f"meal_type must be one of {schemas.MEAL_TYPES}")
        meal = repository.create_planned_meal(conn, data)
        if meal is None:
            raise HTTPException(status_code=404, detail="recipe not found")
        return meal

    @app.delete("/plan/{meal_id}", status_code=204)
    def remove_plan(meal_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        if not repository.delete_planned_meal(conn, meal_id):
            raise HTTPException(status_code=404, detail="planned meal not found")

    # --- Derived: shopping list ---
    @app.get("/shopping-list", response_model=list[schemas.ShoppingListItem])
    def get_shopping_list(start: str | None = None, end: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
        meals = repository.list_planned_meals(conn, start, end)
        recipes = repository.recipes_by_id(conn, {m.recipe_id for m in meals})
        pantry = repository.list_pantry(conn)
        return planner.shopping_list(meals, recipes, pantry)

    # --- Web client: serve the static single-page app ---
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(STATIC_DIR / "index.html")

    return app
