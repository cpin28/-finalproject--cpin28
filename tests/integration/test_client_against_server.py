"""Integration: the real MealPlanClient driving the real app end-to-end.

This is the full stack short of a network socket: client -> ASGI transport -> routes ->
repository -> SQLite. If the CLI/TUI/GUI work, it's because this path works.
"""

from __future__ import annotations


def test_full_planning_flow(api_client):
    flour = api_client.create_ingredient("flour", "g")
    egg = api_client.create_ingredient("egg", "unit")

    recipe = api_client.create_recipe({
        "name": "Pancakes", "servings": 4,
        "ingredients": [
            {"ingredient_id": flour["id"], "quantity": 200, "unit": "g"},
            {"ingredient_id": egg["id"], "quantity": 2, "unit": "unit"},
        ],
    })

    api_client.set_pantry(flour["id"], 50, "g")
    api_client.add_plan("2026-06-10", "breakfast", recipe["id"])

    shopping = api_client.shopping_list()
    by_name = {i["name"]: i for i in shopping}
    assert by_name["flour"]["quantity"] == 150
    assert by_name["egg"]["quantity"] == 2


def test_can_make_reflects_pantry_changes(api_client):
    egg = api_client.create_ingredient("egg", "unit")
    recipe = api_client.create_recipe({
        "name": "Omelette", "servings": 1,
        "ingredients": [{"ingredient_id": egg["id"], "quantity": 3, "unit": "unit"}],
    })
    assert api_client.can_make(recipe["id"])["can_make"] is False
    api_client.set_pantry(egg["id"], 6, "unit")
    assert api_client.can_make(recipe["id"])["can_make"] is True
