"""Contract tests for the /substitutions routes and the recipe `difficulty` field.

These pin the wire contract for the substitution CRUD surface and the substitution-aware
shapes of /recipes/suggestions and /recipes/{id}/can-make.
"""

from __future__ import annotations


def _ingredient(client, name, unit="unit"):
    return client.post("/ingredients", json={"name": name, "default_unit": unit}).json()


def _recipe(client, name, ingredients, difficulty=None, servings=1):
    body = {"name": name, "servings": servings,
            "ingredients": [{"ingredient_id": i, "quantity": q, "unit": u} for i, q, u in ingredients]}
    if difficulty is not None:
        body["difficulty"] = difficulty
    return client.post("/recipes", json=body).json()


# --- substitution CRUD ---------------------------------------------------

def test_create_and_list_substitution_includes_names(client):
    butter = _ingredient(client, "butter", "g")
    oil = _ingredient(client, "oil", "ml")
    resp = client.post("/substitutions", json={
        "ingredient_id": butter["id"], "substitute_id": oil["id"],
        "ratio": 0.75, "note": "use about 3/4 as much oil",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredient_name"] == "butter" and body["substitute_name"] == "oil"
    assert body["ratio"] == 0.75 and body["note"] == "use about 3/4 as much oil"

    listing = client.get("/substitutions").json()
    assert len(listing) == 1
    assert listing[0]["ingredient_name"] == "butter" and listing[0]["substitute_name"] == "oil"


def test_self_substitution_is_422(client):
    egg = _ingredient(client, "egg")
    bad = client.post("/substitutions", json={"ingredient_id": egg["id"], "substitute_id": egg["id"]})
    assert bad.status_code == 422


def test_substitution_with_unknown_ingredient_is_404(client):
    egg = _ingredient(client, "egg")
    assert client.post("/substitutions", json={"ingredient_id": egg["id"], "substitute_id": 999}).status_code == 404
    assert client.post("/substitutions", json={"ingredient_id": 999, "substitute_id": egg["id"]}).status_code == 404


def test_create_substitution_upserts_on_conflict(client):
    butter = _ingredient(client, "butter", "g")
    oil = _ingredient(client, "oil", "ml")
    pair = {"ingredient_id": butter["id"], "substitute_id": oil["id"]}
    client.post("/substitutions", json={**pair, "ratio": 0.75, "note": "first"})
    client.post("/substitutions", json={**pair, "ratio": 0.9, "note": "second"})

    listing = client.get("/substitutions").json()
    assert len(listing) == 1                      # upserted, not duplicated
    assert listing[0]["ratio"] == 0.9 and listing[0]["note"] == "second"


def test_delete_substitution(client):
    butter = _ingredient(client, "butter", "g")
    oil = _ingredient(client, "oil", "ml")
    client.post("/substitutions", json={"ingredient_id": butter["id"], "substitute_id": oil["id"]})

    assert client.delete(f"/substitutions/{butter['id']}/{oil['id']}").status_code == 204
    assert client.get("/substitutions").json() == []
    assert client.delete(f"/substitutions/{butter['id']}/{oil['id']}").status_code == 404  # already gone


# --- substitution-aware derived endpoints --------------------------------

def test_suggestions_surface_makeable_with_substitution(client):
    egg = _ingredient(client, "egg")
    butter = _ingredient(client, "butter", "g")
    oil = _ingredient(client, "oil", "ml")
    _recipe(client, "Pancakes", [(egg["id"], 2, "unit"), (butter["id"], 30, "g")])
    # pantry has egg and oil (not butter); oil substitutes for butter
    client.put("/pantry", json={"ingredient_id": egg["id"], "quantity": 6, "unit": "unit"})
    client.put("/pantry", json={"ingredient_id": oil["id"], "quantity": 250, "unit": "ml"})
    client.post("/substitutions", json={"ingredient_id": butter["id"], "substitute_id": oil["id"],
                                        "ratio": 0.75, "note": "use 3/4 oil"})

    [sug] = client.get("/recipes/suggestions").json()
    assert sug["can_make"] is False
    assert sug["can_make_with_substitutions"] is True
    assert sug["missing"] == []
    assert sug["substitutions"][0]["missing"] == "butter"
    assert sug["substitutions"][0]["use_instead"] == "oil"


def test_can_make_endpoint_reports_substitution(client):
    butter = _ingredient(client, "butter", "g")
    oil = _ingredient(client, "oil", "ml")
    recipe = _recipe(client, "Toast", [(butter["id"], 10, "g")])
    client.put("/pantry", json={"ingredient_id": oil["id"], "quantity": 100, "unit": "ml"})
    client.post("/substitutions", json={"ingredient_id": butter["id"], "substitute_id": oil["id"]})

    check = client.get(f"/recipes/{recipe['id']}/can-make").json()
    assert check["can_make"] is False
    assert check["can_make_with_substitutions"] is True
    assert check["substitutions"][0]["use_instead"] == "oil"


# --- recipe difficulty ---------------------------------------------------

def test_recipe_defaults_to_beginner_difficulty(client):
    egg = _ingredient(client, "egg")
    recipe = _recipe(client, "Boiled Egg", [(egg["id"], 1, "unit")])
    assert recipe["difficulty"] == "beginner"


def test_invalid_difficulty_is_422(client):
    egg = _ingredient(client, "egg")
    bad = client.post("/recipes", json={
        "name": "X", "servings": 1, "difficulty": "expert",
        "ingredients": [{"ingredient_id": egg["id"], "quantity": 1, "unit": "unit"}],
    })
    assert bad.status_code == 422


def test_recipes_filter_by_difficulty(client):
    egg = _ingredient(client, "egg")
    _recipe(client, "Easy One", [(egg["id"], 1, "unit")], difficulty="easy")
    _recipe(client, "Beginner One", [(egg["id"], 1, "unit")], difficulty="beginner")

    easy = client.get("/recipes", params={"difficulty": "easy"}).json()
    assert [r["name"] for r in easy] == ["Easy One"]
