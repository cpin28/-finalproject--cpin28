"""Unit tests for MealPlanClient — does it build the right HTTP requests?

Uses httpx's MockTransport to capture the outgoing request without a server, so these
verify URL construction, methods, query params, and JSON bodies in isolation.
"""

from __future__ import annotations

import json

import httpx

from mealplan_client import MealPlanClient


def client_capturing(into: dict, response: httpx.Response | None = None) -> MealPlanClient:
    def handler(request: httpx.Request) -> httpx.Response:
        into["method"] = request.method
        into["url"] = str(request.url)
        into["body"] = request.content.decode() if request.content else ""
        return response if response is not None else httpx.Response(200, json=[])

    return MealPlanClient("http://test", transport=httpx.MockTransport(handler))


def test_list_recipes_is_a_plain_get():
    seen: dict = {}
    client_capturing(seen).list_recipes()
    assert seen["method"] == "GET" and seen["url"].endswith("/recipes")


def test_search_recipes_sends_query_params():
    seen: dict = {}
    client_capturing(seen).search_recipes("pasta", limit=5)
    assert "/recipes/search" in seen["url"]
    assert "q=pasta" in seen["url"] and "limit=5" in seen["url"]


def test_suggestions_endpoint():
    seen: dict = {}
    client_capturing(seen).suggest_recipes()
    assert seen["method"] == "GET" and "/recipes/suggestions" in seen["url"]


def test_set_pantry_puts_json_body():
    seen: dict = {}
    resp = httpx.Response(200, json={"ingredient_id": 1, "name": "x", "quantity": 2.0, "unit": "g"})
    client_capturing(seen, resp).set_pantry(1, 2.0, "g")
    assert seen["method"] == "PUT" and seen["url"].endswith("/pantry")
    assert json.loads(seen["body"]) == {"ingredient_id": 1, "quantity": 2.0, "unit": "g"}


def test_add_plan_posts_body():
    seen: dict = {}
    resp = httpx.Response(201, json={"id": 1, "date": "2026-06-10", "meal_type": "dinner",
                                     "recipe_id": 1, "recipe_name": "x", "servings": 1})
    client_capturing(seen, resp).add_plan("2026-06-10", "dinner", 1)
    assert seen["method"] == "POST" and seen["url"].endswith("/plan")
    body = json.loads(seen["body"])
    assert body["date"] == "2026-06-10" and body["meal_type"] == "dinner" and body["recipe_id"] == 1


def test_delete_recipe_sends_delete_and_tolerates_204():
    seen: dict = {}
    # a 204 has no body; the client must not try to parse JSON
    client_capturing(seen, httpx.Response(204)).delete_recipe(7)
    assert seen["method"] == "DELETE" and seen["url"].endswith("/recipes/7")


def test_shopping_list_passes_date_range():
    seen: dict = {}
    client_capturing(seen).shopping_list("2026-06-10", "2026-06-16")
    assert "/shopping-list" in seen["url"]
    assert "start=2026-06-10" in seen["url"] and "end=2026-06-16" in seen["url"]
