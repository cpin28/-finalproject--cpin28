"""Meal-planning logic: the derived data that isn't stored anywhere.

These are pure functions over `schemas` objects — no database, no I/O — which is the
whole point: this is the most interesting code to get right, so it's the easiest to
unit-test in isolation.

UNIT HANDLING (the seam, now realised):
    All arithmetic routes through `_canonical()`, which converts a (quantity, unit)
    into a canonical (quantity, base_unit). It currently knows the mass family
    (g/kg) and the volume family (ml/l/tsp/tbsp/cup); units in the same family
    aggregate, different families never combine, and unknown units pass through
    unchanged. Adding more families (e.g. imperial mass) is a one-line edit to
    `_UNIT_FAMILIES` — every aggregation below picks it up for free.
"""

from __future__ import annotations

from collections import defaultdict

from . import schemas


# Unit families: each unit maps to (base_unit, factor_to_base). Units not listed here
# pass through unchanged, so they only combine with an identical label (e.g. "unit").
_UNIT_FAMILIES: dict[str, tuple[str, float]] = {
    "g": ("g", 1.0), "kg": ("g", 1000.0),                 # mass -> grams
    "ml": ("ml", 1.0), "l": ("ml", 1000.0),               # volume -> millilitres
    "tsp": ("ml", 5.0), "tbsp": ("ml", 15.0), "cup": ("ml", 240.0),
}


def _canonical(quantity: float, unit: str) -> tuple[float, str]:
    """Map (quantity, unit) to a canonical (quantity, base_unit) for combining.

    Converts within a unit family (mass, volume) so e.g. 1 kg and 200 g aggregate as
    1200 g; mass and volume have different base units, so they never combine; unknown
    units pass through unchanged.
    """
    base = _UNIT_FAMILIES.get(unit.strip().lower())
    if base is None:
        return quantity, unit
    base_unit, factor = base
    return quantity * factor, base_unit


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


Substitutions = dict[int, list[schemas.Substitution]]


def _evaluate(
    recipe: schemas.Recipe,
    pantry_items: list[schemas.PantryItem],
    substitutions: Substitutions | None,
    servings: int | None = None,
) -> tuple[list[str], list[schemas.SubstitutionOption]]:
    """For one recipe, return (still-missing names, substitution swaps the pantry enables).

    An ingredient that the pantry can't cover directly is filled by the first listed
    substitute the pantry has (presence-based — the ratio/note guide the cook); if none,
    it stays missing.
    """
    have: dict[tuple[int, str], float] = defaultdict(float)
    have_ids: set[int] = set()
    for p in pantry_items:
        qty, unit = _canonical(p.quantity, p.unit)
        have[(p.ingredient_id, unit)] += qty
        if p.quantity > 0:
            have_ids.add(p.ingredient_id)

    base = recipe.servings or 1
    scale = (servings or base) / base
    missing: list[str] = []
    options: list[schemas.SubstitutionOption] = []
    for ri in recipe.ingredients:
        need, unit = _canonical(ri.quantity * scale, ri.unit)
        if have.get((ri.ingredient_id, unit), 0.0) + 1e-9 >= need:
            continue  # covered directly
        option = None
        for sub in (substitutions or {}).get(ri.ingredient_id, []):
            if sub.substitute_id in have_ids:
                option = schemas.SubstitutionOption(
                    missing=ri.name, use_instead=sub.substitute_name, ratio=sub.ratio, note=sub.note)
                break
        if option is not None:
            options.append(option)
        else:
            missing.append(ri.name)
    return missing, options


def cook_status(
    recipe: schemas.Recipe,
    pantry_items: list[schemas.PantryItem],
    substitutions: Substitutions | None = None,
    servings: int | None = None,
) -> schemas.CookCheck:
    """The cook check, now substitution-aware."""
    missing, options = _evaluate(recipe, pantry_items, substitutions, servings)
    return schemas.CookCheck(
        recipe_id=recipe.id,
        can_make=not missing and not options,
        missing=missing,
        can_make_with_substitutions=not missing,
        substitutions=options,
    )


def suggest_recipes(
    recipes: list[schemas.Recipe],
    pantry_items: list[schemas.PantryItem],
    substitutions: Substitutions | None = None,
) -> list[schemas.RecipeSuggestion]:
    """Rank recipes by how well the pantry covers them.

    Order: makeable now, then makeable with a substitution, then fewest still-missing;
    ties break alphabetically. Pure logic, so it's straightforward to unit test.
    """
    suggestions: list[schemas.RecipeSuggestion] = []
    for r in recipes:
        missing, options = _evaluate(r, pantry_items, substitutions)
        need = len(r.ingredients)
        suggestions.append(schemas.RecipeSuggestion(
            recipe_id=r.id, name=r.name, difficulty=r.difficulty,
            can_make=not missing and not options,
            can_make_with_substitutions=not missing,
            missing=missing, substitutions=options,
            have_count=need - len(missing) - len(options), need_count=need,
        ))
    suggestions.sort(key=lambda s: (
        0 if s.can_make else 1 if s.can_make_with_substitutions else 2,
        len(s.missing), s.name.lower(),
    ))
    return suggestions
