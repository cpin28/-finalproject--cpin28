# Testing

Three levels, matching the architecture. Each layer is tested where it's cheapest and
clearest to test it.

```
tests/
  unit/         planner logic — pure functions, no DB, no HTTP
  contract/     the REST API's status codes & response shapes (FastAPI TestClient)
  integration/  repository against real SQLite, and the real client against the app
```

## Unit (`tests/unit/test_planner.py`)

The planner is the most interesting code, so it gets the most cases: scaling by
servings, aggregating an ingredient across multiple meals, subtracting pantry stock,
the same-unit rule, the cook check, and output ordering. No database — objects are built
by hand, so these tests are fast and pin the behaviour precisely.

## Contract (`tests/contract/test_api_contract.py`)

Drives the API through FastAPI's `TestClient`. Asserts the things clients rely on:
- `201` on create, `404` for missing resources, `409` on duplicate ingredient,
  `422` on an invalid meal type;
- recipes come back with joined ingredient names;
- the shopping-list response is exactly `{ingredient_id, name, quantity, unit}` and
  reflects pantry stock.

## Integration (`tests/integration/`)

- `test_repository_with_real_db.py` — repository against a temp SQLite file: joins, the
  pantry upsert, the foreign-key cascade on delete, date-range filtering.
- `test_client_against_server.py` — the real `MealPlanClient` over an in-process ASGI
  transport, exercising client → routes → repository → SQLite end to end.

## Running

```bash
uv run pytest                 # everything
uv run pytest tests/unit      # just the fast logic tests
uv run pytest -q
```

## Fixtures (`tests/conftest.py`)

`conn` (real temp DB), `client` (TestClient), and `api_client` (the real client wired to
the app in-process) — one fixture per test level so each test asks for exactly the layer
it needs.
