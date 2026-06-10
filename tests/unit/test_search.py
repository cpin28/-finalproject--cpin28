"""Unit tests for fuzzy search scoring — pure logic, no database."""

from __future__ import annotations

from server import schemas, search


def recipe(rid, name):
    return schemas.Recipe(id=rid, name=name, servings=1)


def test_exact_match_scores_highest():
    assert search.fuzzy_score("Pancakes", "Pancakes") == 1.0


def test_case_insensitive():
    assert search.fuzzy_score("pancakes", "PANCAKES") == 1.0


def test_prefix_beats_substring_beats_subsequence():
    prefix = search.fuzzy_score("pan", "pancakes")        # starts-with
    substr = search.fuzzy_score("cake", "pancakes")       # substring
    subseq = search.fuzzy_score("pnks", "pancakes")       # gapped subsequence
    assert prefix > substr > subseq > 0.0


def test_non_subsequence_scores_zero():
    assert search.fuzzy_score("xyz", "pancakes") == 0.0


def test_empty_query_scores_zero():
    assert search.fuzzy_score("", "pancakes") == 0.0


def test_contiguous_subsequence_beats_spread_out():
    tight = search.fuzzy_score("cak", "pancakes")   # 'cak' contiguous
    loose = search.fuzzy_score("pck", "pancakes")   # p..c..k spread out
    assert tight > loose


def test_rank_orders_best_first_and_filters_non_matches():
    recipes = [recipe(1, "Tomato Pasta"), recipe(2, "Pancakes"), recipe(3, "Chicken Pasta")]
    ranked = search.rank_recipes("pasta", recipes)
    names = [r.name for _s, r in ranked]
    # both pasta dishes match (substring), pancakes does not
    assert "Pancakes" not in names
    assert set(names) == {"Tomato Pasta", "Chicken Pasta"}


def test_rank_ties_break_alphabetically():
    recipes = [recipe(1, "Pasta Verde"), recipe(2, "Pasta Bianca")]
    ranked = search.rank_recipes("pasta", recipes)
    assert [r.name for _s, r in ranked] == ["Pasta Bianca", "Pasta Verde"]
