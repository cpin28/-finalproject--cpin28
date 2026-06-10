"""Data access layer, split one module per entity.

Was a single ~190-line `repository.py`; refactored into per-entity modules
(`ingredients`, `recipes`, `pantry`, `plan`). The public surface is unchanged — every
function is re-exported here, so callers still write `repository.create_recipe(...)`.

The rule still holds: every SQL statement lives in this package, and these functions
return plain `schemas` objects so nothing above ever sees a raw row.
"""

from __future__ import annotations

from .ingredients import create_ingredient, get_ingredient, list_ingredients
from .pantry import list_pantry, remove_pantry_item, set_pantry_item
from .plan import create_planned_meal, delete_planned_meal, list_planned_meals
from .recipes import (
    create_recipe,
    delete_recipe,
    get_recipe,
    list_recipes,
    recipes_by_id,
)

__all__ = [
    "create_ingredient",
    "get_ingredient",
    "list_ingredients",
    "create_recipe",
    "delete_recipe",
    "get_recipe",
    "list_recipes",
    "recipes_by_id",
    "list_pantry",
    "remove_pantry_item",
    "set_pantry_item",
    "create_planned_meal",
    "delete_planned_meal",
    "list_planned_meals",
]
