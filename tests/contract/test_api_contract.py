"""Contract tests: assert the HTTP API's status codes and response shapes.

These pin the wire contract that every client depends on. They hit the app via
FastAPI's TestClient — real routing and validation, in-memory storage.
"""

from __future__ import annotations


def _ingredient(client, name, unit="unit"):
    return client.post("/ingredients", json={"name": name, "default_unit": unit}).json()


def test_create_and_list_ingredient(client):
    resp = client.post("/ingredients", json={"name": "flour", "default_unit": "g"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0 and body["name"] == "flour" and body["default_unit"] == "g"

    listing = client.get("/ingredients").json()
    assert [i["name"] for i in listing] == ["flour"]


def test_duplicate_ingredient_conflicts(client):
    _ingredient(client, "egg")
    assert client.post("/ingredients", json={"name": "egg"}).status_code == 409


def test_recipe_roundtrip_includes_ingredient_names(client):
    flour = _ingredient(client, "flour", "g")
    recipe = client.post("/recipes", json={
        "name": "Bread", "servings": 2,
        "ingredients": [{"ingredient_id": flour["id"], "quantity": 500, "unit": "g"}],
    }).json()
    assert recipe["id"] > 0
    fetched = client.get(f"/recipes/{recipe['id']}").json()
    assert fetched["ingredients"][0]["name"] == "flour"
    assert fetched["ingredients"][0]["quantity"] == 500


def test_missing_recipe_is_404(client):
    assert client.get("/recipes/999").status_code == 404


def test_invalid_meal_type_is_422(client):
    flour = _ingredient(client, "flour", "g")
    recipe = client.post("/recipes", json={"name": "X", "servings": 1,
                                           "ingredients": [{"ingredient_id": flour["id"], "quantity": 1, "unit": "g"}]}).json()
    bad = client.post("/plan", json={"date": "2026-06-10", "meal_type": "brunch", "recipe_id": recipe["id"]})
    assert bad.status_code == 422


def test_shopping_list_shape_reflects_pantry(client):
    flour = _ingredient(client, "flour", "g")
    recipe = client.post("/recipes", json={"name": "Bread", "servings": 1,
                                           "ingredients": [{"ingredient_id": flour["id"], "quantity": 500, "unit": "g"}]}).json()
    client.post("/plan", json={"date": "2026-06-10", "meal_type": "dinner", "recipe_id": recipe["id"]})
    client.put("/pantry", json={"ingredient_id": flour["id"], "quantity": 200, "unit": "g"})

    items = client.get("/shopping-list").json()
    assert len(items) == 1
    assert items[0] == {"ingredient_id": flour["id"], "name": "flour", "quantity": 300, "unit": "g"}


def test_can_make_endpoint(client):
    egg = _ingredient(client, "egg")
    recipe = client.post("/recipes", json={"name": "Omelette", "servings": 1,
                                           "ingredients": [{"ingredient_id": egg["id"], "quantity": 3, "unit": "unit"}]}).json()
    assert client.get(f"/recipes/{recipe['id']}/can-make").json()["can_make"] is False
    client.put("/pantry", json={"ingredient_id": egg["id"], "quantity": 6, "unit": "unit"})
    assert client.get(f"/recipes/{recipe['id']}/can-make").json()["can_make"] is True
