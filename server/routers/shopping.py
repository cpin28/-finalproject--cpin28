"""Route for the derived shopping list."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import planner, repository, schemas
from ..deps import get_conn

router = APIRouter(tags=["shopping"])


@router.get("/shopping-list", response_model=list[schemas.ShoppingListItem])
def get_shopping_list(start: str | None = None, end: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    meals = repository.list_planned_meals(conn, start, end)
    recipes = repository.recipes_by_id(conn, {m.recipe_id for m in meals})
    pantry = repository.list_pantry(conn)
    return planner.shopping_list(meals, recipes, pantry)
