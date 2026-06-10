"""Shared HTTP client for the mealplan API.

Every client (CLI, TUI, GUI) goes through this one class instead of building URLs and
parsing JSON itself. That keeps the wire protocol in a single place and means the
integration tests can drive the *real* client against an in-process app.
"""

from __future__ import annotations

from typing import Any

import httpx


class MealPlanClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", *, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url, transport=transport, timeout=10.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "MealPlanClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _json(self, resp: httpx.Response) -> Any:
        resp.raise_for_status()
        return resp.json() if resp.content else None

    # --- Ingredients ---
    def list_ingredients(self) -> list[dict]:
        return self._json(self._http.get("/ingredients"))

    def create_ingredient(self, name: str, default_unit: str = "unit") -> dict:
        return self._json(self._http.post("/ingredients", json={"name": name, "default_unit": default_unit}))

    # --- Recipes ---
    def list_recipes(self, q: str | None = None) -> list[dict]:
        return self._json(self._http.get("/recipes", params={"q": q} if q else None))

    def search_recipes(self, q: str, limit: int = 10) -> list[dict]:
        return self._json(self._http.get("/recipes/search", params={"q": q, "limit": limit}))

    def suggest_recipes(self, limit: int = 10) -> list[dict]:
        return self._json(self._http.get("/recipes/suggestions", params={"limit": limit}))

    def get_recipe(self, recipe_id: int) -> dict:
        return self._json(self._http.get(f"/recipes/{recipe_id}"))

    def create_recipe(self, recipe: dict) -> dict:
        return self._json(self._http.post("/recipes", json=recipe))

    def delete_recipe(self, recipe_id: int) -> None:
        self._json(self._http.delete(f"/recipes/{recipe_id}"))

    def can_make(self, recipe_id: int, servings: int | None = None) -> dict:
        return self._json(self._http.get(f"/recipes/{recipe_id}/can-make", params={"servings": servings} if servings else None))

    # --- Pantry ---
    def list_pantry(self) -> list[dict]:
        return self._json(self._http.get("/pantry"))

    def set_pantry(self, ingredient_id: int, quantity: float, unit: str) -> dict:
        return self._json(self._http.put("/pantry", json={"ingredient_id": ingredient_id, "quantity": quantity, "unit": unit}))

    def remove_pantry(self, ingredient_id: int) -> None:
        self._json(self._http.delete(f"/pantry/{ingredient_id}"))

    # --- Meal plan ---
    def list_plan(self, start: str | None = None, end: str | None = None) -> list[dict]:
        return self._json(self._http.get("/plan", params={"start": start, "end": end}))

    def add_plan(self, date: str, meal_type: str, recipe_id: int, servings: int | None = None) -> dict:
        body = {"date": date, "meal_type": meal_type, "recipe_id": recipe_id, "servings": servings}
        return self._json(self._http.post("/plan", json=body))

    def remove_plan(self, meal_id: int) -> None:
        self._json(self._http.delete(f"/plan/{meal_id}"))

    # --- Derived ---
    def shopping_list(self, start: str | None = None, end: str | None = None) -> list[dict]:
        return self._json(self._http.get("/shopping-list", params={"start": start, "end": end}))
