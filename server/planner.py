"""Meal-planning logic: the derived data that isn't stored anywhere.

These are pure functions over `schemas` objects — no database, no I/O — which is the
whole point: this is the most interesting code to get right, so it's the easiest to
unit-test in isolation.

UNIT HANDLING (the seam):
    Right now units are treated as opaque labels. Two quantities only combine when
    their unit strings match; otherwise they're tracked separately. All arithmetic
    is routed through `_canonical()`, so adding real conversions later (g<->kg,
    ml<->l, cups<->ml) means implementing *only* that one function and widening the
    key it returns — every aggregation below picks it up for free.
"""

from __future__ import annotations

from collections import defaultdict

from . import schemas


def _canonical(quantity: float, unit: str) -> tuple[float, str]:
    """Map (quantity, unit) to a canonical (quantity, unit) for combining.

    Identity for now. Replace with conversion logic to support unit families.
    """
    return quantity, unit


def required_ingredients(
    planned_meals: list[schemas.PlannedMeal],
    recipes_by_id: dict[int, schemas.Recipe],
) -> dict[tuple[int, str], schemas.ShoppingListItem]:
    """Total quantity of each (ingredient, unit) needed across the planned meals.

    Each recipe is scaled by (planned servings / recipe servings).
    """
    totals: dict[tuple[int, str], schemas.ShoppingListItem] = {}
    for meal in planned_meals:
        recipe = recipes_by_id.get(meal.recipe_id)
        if recipe is None:
            continue
        base = recipe.servings or 1
        scale = (meal.servings or base) / base
        for ri in recipe.ingredients:
            qty, unit = _canonical(ri.quantity * scale, ri.unit)
            key = (ri.ingredient_id, unit)
            if key in totals:
                totals[key].quantity += qty
            else:
                totals[key] = schemas.ShoppingListItem(
                    ingredient_id=ri.ingredient_id, name=ri.name, quantity=qty, unit=unit
                )
    return totals


def shopping_list(
    planned_meals: list[schemas.PlannedMeal],
    recipes_by_id: dict[int, schemas.Recipe],
    pantry_items: list[schemas.PantryItem],
) -> list[schemas.ShoppingListItem]:
    """What still needs buying: required minus what's already in the pantry."""
    have: dict[tuple[int, str], float] = defaultdict(float)
    for p in pantry_items:
        qty, unit = _canonical(p.quantity, p.unit)
        have[(p.ingredient_id, unit)] += qty

    items: list[schemas.ShoppingListItem] = []
    for key, item in required_ingredients(planned_meals, recipes_by_id).items():
        remaining = item.quantity - have.get(key, 0.0)
        if remaining > 1e-9:
            items.append(item.model_copy(update={"quantity": round(remaining, 4)}))
    items.sort(key=lambda i: i.name.lower())
    return items


def missing_for_recipe(
    recipe: schemas.Recipe,
    pantry_items: list[schemas.PantryItem],
    servings: int | None = None,
) -> list[str]:
    """Names of ingredients the pantry can't cover for one recipe (same-unit check)."""
    have: dict[tuple[int, str], float] = defaultdict(float)
    for p in pantry_items:
        qty, unit = _canonical(p.quantity, p.unit)
        have[(p.ingredient_id, unit)] += qty

    base = recipe.servings or 1
    scale = (servings or base) / base
    missing: list[str] = []
    for ri in recipe.ingredients:
        need, unit = _canonical(ri.quantity * scale, ri.unit)
        if have.get((ri.ingredient_id, unit), 0.0) + 1e-9 < need:
            missing.append(ri.name)
    return missing


def can_make(
    recipe: schemas.Recipe,
    pantry_items: list[schemas.PantryItem],
    servings: int | None = None,
) -> bool:
    return not missing_for_recipe(recipe, pantry_items, servings)
