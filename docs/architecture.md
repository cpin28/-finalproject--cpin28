# Architecture

## Overview

A client–server application. A single FastAPI server owns an SQLite database and exposes
a REST API. Three Python clients (CLI, TUI, GUI) talk to it through one shared client
library; a fourth client — a browser web UI — is static files served by the server and
calls the same REST API directly with `fetch`.

```
 ┌────────┐   ┌────────┐   ┌────────┐      ┌──────────┐
 │  CLI   │   │  TUI   │   │  GUI   │      │  Web UI  │   (static/, fetch)
 └───┬────┘   └───┬────┘   └───┬────┘      └────┬─────┘
     └────────────┼────────────┘                │
            mealplan_client (httpx)             │  HTTP/JSON
                  │  HTTP/JSON                   │
                  └───────────────┬─────────────┘
            ┌─────▼─────┐
            │  api.py   │   FastAPI routes — validate, delegate, return schemas
            ├───────────┤
            │ planner   │   derived data (shopping list, cook check) — pure functions
            ├───────────┤
            │ repository│   all SQL lives here; returns schema objects
            ├───────────┤
            │   db.py   │   SQLite connection + schema (only module that imports sqlite3)
            └─────┬─────┘
            ┌─────▼─────┐
            │  SQLite   │
            └───────────┘
```

## Layers (server)

| Module | Responsibility | Depends on |
|---|---|---|
| `db.py` | connection + schema | sqlite3 |
| `repository/` | CRUD, all SQL — one module per entity | db, schemas |
| `planner.py` | shopping list, cook check, pantry suggestions — pure logic | schemas |
| `search.py` | fuzzy recipe-name scoring & ranking — pure logic | schemas |
| `schemas.py` | wire/data models (Pydantic) | — |
| `deps.py` | shared FastAPI dependency (per-request connection) | db |
| `routers/` | HTTP routes, one module per resource | repository, planner, schemas, deps |
| `api.py` | app assembly: include routers + serve web client | routers, db |
| `main.py` | uvicorn entry | api |

The dependency arrows only point downward. `planner` has no I/O, which is what lets the
unit tests run it with hand-built objects and no database.

Both the route layer and the data layer are split per resource. `routers/` has one
`APIRouter` module per resource (`ingredients`, `recipes`, `pantry`, `plan`,
`shopping`) that `api.py` includes; `repository/` has one SQL module per entity, with
`__init__.py` re-exporting the functions so callers still write `repository.create_recipe(...)`.
(Both were refactored out of single monolithic modules — a ~135-line `create_app()` and a
~190-line `repository.py`; see the git history.) Adding a resource is now a new router
module plus a new repository module — each small and focused.

## Data model

- `ingredients (id, name unique, default_unit)`
- `recipes (id, name, description, instructions, servings, prep_time_minutes)`
- `recipe_ingredients (recipe_id → recipes, ingredient_id → ingredients, quantity, unit)`  — many-to-many
- `pantry_items (ingredient_id → ingredients [PK], quantity, unit)`
- `planned_meals (id, date, meal_type, recipe_id → recipes, servings)`

## REST API surface

| Method & path | Purpose |
|---|---|
| `GET/POST /ingredients` | list / create ingredients |
| `GET/POST /recipes`, `GET/DELETE /recipes/{id}` | manage recipes (`?q=` filters by name) |
| `GET /recipes/search?q=` | fuzzy-ranked recipe search (`search.py`) |
| `GET /recipes/suggestions` | recipes ranked by pantry coverage (`planner.suggest_recipes`) |
| `GET /recipes/{id}/can-make` | cook check against the pantry |
| `GET /pantry`, `PUT /pantry`, `DELETE /pantry/{ingredient_id}` | pantry stock |
| `GET/POST /plan`, `DELETE /plan/{id}` | weekly meal plan (`?start=&end=`) |
| `GET /shopping-list` | derived list for a date range (`?start=&end=`) |
