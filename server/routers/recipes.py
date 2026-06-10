"""Routes for recipes, including the pantry-aware cook check."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import planner, repository, schemas
from ..deps import get_conn

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[schemas.Recipe])
def list_recipes(q: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    return repository.list_recipes(conn, q)


@router.post("", response_model=schemas.Recipe, status_code=201)
def create_recipe(data: schemas.RecipeCreate, conn: sqlite3.Connection = Depends(get_conn)):
    return repository.create_recipe(conn, data)


@router.get("/{recipe_id}", response_model=schemas.Recipe)
def get_recipe(recipe_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    recipe = repository.get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="recipe not found")
    return recipe


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    if not repository.delete_recipe(conn, recipe_id):
        raise HTTPException(status_code=404, detail="recipe not found")


@router.get("/{recipe_id}/can-make", response_model=schemas.CookCheck)
def can_make(recipe_id: int, servings: int | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    recipe = repository.get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="recipe not found")
    pantry = repository.list_pantry(conn)
    missing = planner.missing_for_recipe(recipe, pantry, servings)
    return schemas.CookCheck(recipe_id=recipe_id, can_make=not missing, missing=missing)
