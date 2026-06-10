"""TDD: unit conversion in planner._canonical.

These tests were written BEFORE the implementation (the "red" step) to drive the design
of the unit-conversion feature, then `planner._canonical` was implemented to make them
pass (the "green" step). The two are separate commits — see the git history.

Until now units were opaque labels (combine only when the strings matched). The feature:
convert within a family (mass g/kg, volume ml/l/tsp/tbsp/cup) so quantities in different
units of the same family aggregate correctly; cross-family and unknown units stay separate.
"""

from __future__ import annotations

from server import planner, schemas


def recipe(rid, name, servings, ingredients):
    return schemas.Recipe(
        id=rid, name=name, servings=servings,
        ingredients=[schemas.RecipeIngredient(ingredient_id=i, name=n, quantity=q, unit=u) for i, n, q, u in ingredients],
    )


def meal(mid, recipe_id, servings):
    return schemas.PlannedMeal(id=mid, date="2026-06-10", meal_type="dinner", recipe_id=recipe_id, recipe_name="x", servings=servings)


def pantry(items):
    return [schemas.PantryItem(ingredient_id=i, name=n, quantity=q, unit=u) for i, n, q, u in items]


# --- _canonical itself ---------------------------------------------------

def test_canonical_converts_kg_to_grams():
    assert planner._canonical(1, "kg") == (1000.0, "g")


def test_canonical_converts_litres_to_millilitres():
    assert planner._canonical(2, "l") == (2000.0, "ml")


def test_canonical_converts_cooking_volumes_to_millilitres():
    assert planner._canonical(1, "cup") == (240.0, "ml")
    assert planner._canonical(1, "tbsp") == (15.0, "ml")
    assert planner._canonical(1, "tsp") == (5.0, "ml")


def test_canonical_is_case_insensitive():
    assert planner._canonical(1, "KG") == (1000.0, "g")


def test_canonical_passes_through_unknown_units():
    assert planner._canonical(3, "unit") == (3, "unit")
    assert planner._canonical(2, "pinch") == (2, "pinch")


# --- behaviour through the shopping list ---------------------------------

def test_pantry_in_kg_covers_recipe_in_grams():
    r = recipe(1, "Bread", 1, [(10, "flour", 500, "g")])
    items = planner.shopping_list([meal(1, 1, 1)], {1: r}, pantry([(10, "flour", 1, "kg")]))
    assert items == []  # 1 kg covers 500 g


def test_required_combines_across_units_in_a_family():
    # one recipe needs 1 kg, another 200 g of the same ingredient -> 1200 g total
    r1 = recipe(1, "A", 1, [(10, "flour", 1, "kg")])
    r2 = recipe(2, "B", 1, [(10, "flour", 200, "g")])
    items = planner.shopping_list([meal(1, 1, 1), meal(2, 2, 1)], {1: r1, 2: r2}, [])
    assert len(items) == 1 and items[0].unit == "g" and items[0].quantity == 1200


def test_mass_and_volume_never_combine():
    r = recipe(1, "X", 1, [(10, "water", 100, "g"), (11, "milk", 100, "ml")])
    items = planner.shopping_list([meal(1, 1, 1)], {1: r}, [])
    assert sorted(i.unit for i in items) == ["g", "ml"]
