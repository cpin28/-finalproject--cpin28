"""Unit tests for the planner's substitution awareness — pure logic, no database.

Covers `cook_status` (the substitution-aware cook check) and the substitution branch of
`suggest_recipes`: a gap the pantry can't cover directly is filled by the first listed
substitute the pantry has, which lifts a recipe from "missing" to "makeable with a
substitution" without making it count as directly makeable.
"""

from __future__ import annotations

from server import planner, schemas


def recipe(rid, name, servings, ingredients):
    return schemas.Recipe(
        id=rid, name=name, servings=servings,
        ingredients=[schemas.RecipeIngredient(ingredient_id=i, name=n, quantity=q, unit=u) for i, n, q, u in ingredients],
    )


def pantry(items):
    return [schemas.PantryItem(ingredient_id=i, name=n, quantity=q, unit=u) for i, n, q, u in items]


def subs(rows):
    """Build the planner's substitutions map from (ing_id, ing_name, sub_id, sub_name, ratio, note) rows."""
    out: dict[int, list[schemas.Substitution]] = {}
    for ing_id, ing_name, sub_id, sub_name, ratio, note in rows:
        out.setdefault(ing_id, []).append(schemas.Substitution(
            ingredient_id=ing_id, ingredient_name=ing_name,
            substitute_id=sub_id, substitute_name=sub_name, ratio=ratio, note=note,
        ))
    return out


# --- cook_status ---------------------------------------------------------

def test_cook_status_direct_cover():
    r = recipe(1, "Boiled Egg", 1, [(10, "egg", 2, "unit")])
    status = planner.cook_status(r, pantry([(10, "egg", 6, "unit")]))
    assert status.can_make is True
    assert status.can_make_with_substitutions is True  # trivially: nothing to fill
    assert status.missing == [] and status.substitutions == []


def test_cook_status_uses_pantry_substitute():
    # recipe needs butter; pantry has oil; oil substitutes for butter
    r = recipe(1, "Pancakes", 1, [(10, "flour", 100, "g"), (11, "butter", 30, "g")])
    have = pantry([(10, "flour", 500, "g"), (12, "oil", 250, "ml")])
    s = subs([(11, "butter", 12, "oil", 0.75, "use about 3/4 as much oil")])
    status = planner.cook_status(r, have, s)
    assert status.can_make is False                    # not directly makeable
    assert status.can_make_with_substitutions is True  # the gap is fillable
    assert status.missing == []
    assert len(status.substitutions) == 1
    opt = status.substitutions[0]
    assert opt.missing == "butter" and opt.use_instead == "oil"
    assert opt.ratio == 0.75 and opt.note == "use about 3/4 as much oil"


def test_cook_status_substitute_absent_stays_missing():
    # butter substitutes for oil, but the pantry has neither butter nor oil
    r = recipe(1, "Pancakes", 1, [(11, "butter", 30, "g")])
    s = subs([(11, "butter", 12, "oil", 0.75, "")])
    status = planner.cook_status(r, pantry([]), s)
    assert status.can_make is False
    assert status.can_make_with_substitutions is False
    assert status.missing == ["butter"] and status.substitutions == []


def test_cook_status_picks_first_listed_substitute_in_pantry():
    # two registered substitutes; only the second is in the pantry, so it's chosen
    r = recipe(1, "Cake", 1, [(11, "milk", 100, "ml")])
    have = pantry([(13, "water", 500, "ml")])
    s = subs([
        (11, "milk", 12, "yogurt", 1.0, "thin with water"),
        (11, "milk", 13, "water", 1.0, "lighter and less rich"),
    ])
    status = planner.cook_status(r, have, s)
    assert status.can_make_with_substitutions is True
    assert [o.use_instead for o in status.substitutions] == ["water"]


def test_cook_status_scales_by_servings_before_substituting():
    # direct cover at 1 serving, but 4 servings outstrips the pantry and falls to the sub
    r = recipe(1, "Scramble", 1, [(11, "milk", 50, "ml")])
    have = pantry([(11, "milk", 60, "ml"), (12, "water", 500, "ml")])
    s = subs([(11, "milk", 12, "water", 1.0, "")])
    assert planner.cook_status(r, have, s, servings=1).can_make is True
    scaled = planner.cook_status(r, have, s, servings=4)
    assert scaled.can_make is False
    assert scaled.can_make_with_substitutions is True
    assert [o.use_instead for o in scaled.substitutions] == ["water"]


# --- suggest_recipes ranking ---------------------------------------------

def test_suggestions_rank_makeable_then_substitutable_then_missing():
    makeable = recipe(1, "Makeable", 1, [(10, "egg", 2, "unit")])
    sub_ok = recipe(2, "Substitutable", 1, [(10, "egg", 2, "unit"), (11, "butter", 30, "g")])
    missing = recipe(3, "Missing", 1, [(10, "egg", 2, "unit"), (13, "saffron", 1, "g")])
    have = pantry([(10, "egg", 6, "unit"), (12, "oil", 250, "ml")])
    s = subs([(11, "butter", 12, "oil", 0.75, "")])

    ranked = planner.suggest_recipes([missing, sub_ok, makeable], have, s)
    assert [r.name for r in ranked] == ["Makeable", "Substitutable", "Missing"]
    assert ranked[0].can_make is True
    assert ranked[1].can_make is False and ranked[1].can_make_with_substitutions is True
    assert ranked[2].can_make_with_substitutions is False and ranked[2].missing == ["saffron"]


def test_suggestion_counts_exclude_substitutions_from_have():
    # one direct (egg), one filled by substitute (butter->oil): have_count counts only the direct
    r = recipe(1, "Pancakes", 1, [(10, "egg", 2, "unit"), (11, "butter", 30, "g")])
    have = pantry([(10, "egg", 6, "unit"), (12, "oil", 250, "ml")])
    s = subs([(11, "butter", 12, "oil", 0.75, "")])
    [sug] = planner.suggest_recipes([r], have, s)
    assert sug.need_count == 2
    assert sug.have_count == 1                # egg only; butter is covered via a substitution
    assert sug.missing == [] and len(sug.substitutions) == 1
    assert sug.difficulty == "beginner"      # carried through from the recipe
