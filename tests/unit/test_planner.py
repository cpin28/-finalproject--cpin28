"""Unit tests for the planner — pure logic, no database.

This is the heart of the app, so it gets the most thorough coverage: scaling by
servings, aggregating the same ingredient across meals, subtracting pantry stock, and
the same-unit rule.
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


def test_required_scales_by_servings():
    r = recipe(1, "Pasta", servings=2, ingredients=[(10, "pasta", 200, "g")])
    totals = planner.required_ingredients([meal(1, 1, servings=4)], {1: r})
    # 4 servings of a 2-serving recipe = 2x => 400g
    assert totals[(10, "g")].quantity == 400


def test_required_aggregates_same_ingredient_across_meals():
    r1 = recipe(1, "A", 1, [(10, "onion", 1, "unit")])
    r2 = recipe(2, "B", 1, [(10, "onion", 2, "unit")])
    totals = planner.required_ingredients([meal(1, 1, 1), meal(2, 2, 1)], {1: r1, 2: r2})
    assert totals[(10, "unit")].quantity == 3


def test_shopping_list_subtracts_pantry():
    r = recipe(1, "Pancakes", 4, [(10, "flour", 200, "g"), (11, "egg", 2, "unit")])
    items = planner.shopping_list([meal(1, 1, 4)], {1: r}, pantry([(10, "flour", 50, "g")]))
    by_name = {i.name: i for i in items}
    assert by_name["flour"].quantity == 150  # 200 needed - 50 in pantry
    assert by_name["egg"].quantity == 2       # none in pantry


def test_shopping_list_omits_fully_covered():
    r = recipe(1, "Rice", 2, [(10, "rice", 100, "g")])
    items = planner.shopping_list([meal(1, 1, 2)], {1: r}, pantry([(10, "rice", 500, "g")]))
    assert items == []


def test_pantry_partial_cover_across_units():
    # units convert within a family: 0.3 kg in the pantry offsets a 500 g requirement,
    # leaving 200 g to buy (see test_unit_conversion.py for the full conversion behaviour)
    r = recipe(1, "Bread", 1, [(10, "flour", 500, "g")])
    items = planner.shopping_list([meal(1, 1, 1)], {1: r}, pantry([(10, "flour", 0.3, "kg")]))
    assert len(items) == 1 and items[0].unit == "g" and items[0].quantity == 200


def test_can_make_and_missing():
    r = recipe(1, "Omelette", 1, [(11, "egg", 3, "unit"), (12, "milk", 50, "ml")])
    have = pantry([(11, "egg", 6, "unit")])
    assert planner.can_make(r, have) is False
    assert planner.missing_for_recipe(r, have) == ["milk"]
    assert planner.can_make(r, pantry([(11, "egg", 6, "unit"), (12, "milk", 100, "ml")])) is True


def test_shopping_list_sorted_by_name():
    r = recipe(1, "Mix", 1, [(2, "zucchini", 1, "unit"), (1, "apple", 1, "unit")])
    items = planner.shopping_list([meal(1, 1, 1)], {1: r}, [])
    assert [i.name for i in items] == ["apple", "zucchini"]


def test_suggestions_rank_makeable_first_then_fewest_missing():
    r1 = recipe(1, "Makeable", 1, [(10, "egg", 2, "unit")])
    r2 = recipe(2, "OneMissing", 1, [(10, "egg", 2, "unit"), (11, "milk", 50, "ml")])
    r3 = recipe(3, "TwoMissing", 1, [(11, "milk", 50, "ml"), (12, "flour", 100, "g")])
    have = pantry([(10, "egg", 6, "unit")])
    suggestions = planner.suggest_recipes([r3, r2, r1], have)
    assert [s.name for s in suggestions] == ["Makeable", "OneMissing", "TwoMissing"]
    assert suggestions[0].can_make is True
    assert suggestions[1].missing == ["milk"]


def test_suggestion_counts():
    r = recipe(1, "Omelette", 1, [(10, "egg", 3, "unit"), (11, "milk", 50, "ml")])
    [s] = planner.suggest_recipes([r], pantry([(10, "egg", 6, "unit")]))
    assert s.need_count == 2 and s.have_count == 1 and s.missing == ["milk"]
