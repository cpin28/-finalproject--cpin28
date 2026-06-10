# Testing

Three levels, matching the architecture — each component tested where it's cheapest and
clearest. The suite covers both the server *and* the clients.

```
tests/
  unit/                pure logic & parsing — no DB, no network
    test_planner.py        shopping list, cook check, suggestions
    test_unit_conversion.py unit-family conversion (built test-first — see below)
    test_search.py          fuzzy scoring & ranking
    cli/                    CLI argument parsing
    client/                 MealPlanClient request building (httpx MockTransport)
  contract/            the REST API's shapes, plus the served web client (JS + endpoints)
  integration/         real SQLite, the real client/TUI/GUI over a live server
```

## Unit (`tests/unit/`)

Pure functions and parsing, built by hand — fast, no I/O.

- **`test_planner.py`** — the planner: scaling by servings, aggregating an ingredient
  across meals, subtracting pantry stock, cross-unit partial cover, the cook check,
  suggestion ranking, output ordering.
- **`test_unit_conversion.py`** — the mass/volume conversion in `_canonical`. **Written
  test-first**: the tests were committed failing (`TDD (red)`), then the implementation
  made them pass (`TDD (green)`) — see the git history.
- **`test_search.py`** — the fuzzy scorer (exact/prefix/substring/subsequence tiers,
  ranking order, non-matches scoring zero).
- **`cli/test_argument_parsing.py`** — the CLI parser: each subcommand maps to the right
  handler and coerces its arguments (ints, floats, the 3-value `plan --add`).
- **`client/test_client_requests.py`** — `MealPlanClient` builds the right requests
  (method, URL, query params, JSON body), captured with httpx's `MockTransport` — no
  server needed.

## Contract (`tests/contract/`)

Drives the API through FastAPI's `TestClient`. Asserts what clients rely on: `201` on
create, `404`/`409`/`422` on the error paths, joined ingredient names, the exact
shopping-list/suggestion shapes, and that `/recipes/search` isn't shadowed by
`/recipes/{id}`. `test_web_client.py` covers the web client: the files are served,
`app.js` is valid JavaScript (`node --check`), and every endpoint the JS calls matches a
real route on the app — a guard against client/server drift (a full browser DOM test is
deliberately out of scope).

## Integration (`tests/integration/`)

- **`test_repository_with_real_db.py`** — repository against a temp SQLite file: joins, the
  pantry upsert, the foreign-key cascade on delete, date-range filtering.
- **`test_client_against_server.py`** — the real `MealPlanClient` driving the real app on a
  **live uvicorn server** (background thread, real socket): client → routes → repository →
  SQLite, end to end.
- **`test_tui_pilot.py`** — the real `MealPlanTUI` driven headlessly via Textual's
  `run_test` pilot against a live seeded server: it loads recipes, renders suggestions, and
  fuzzy-searches — the interactive-client analogue of the test above.
- **`test_gui_smoke.py`** — the real tkinter `MealPlanGUI` against a live server: loads
  every tab and fuzzy-searches. Skips cleanly where there's no display (headless CI).

## Running

```bash
uv run pytest                 # everything (62 tests)
uv run pytest tests/unit      # just the fast logic/parsing tests
uv run pytest -q
```

## Fixtures (`tests/conftest.py`)

One fixture per level, so each test asks for exactly the layer it needs:
- `conn` — a real connection to a temp SQLite database
- `client` — FastAPI `TestClient` (in-process routing)
- `live_server` — the app under a real uvicorn server in a background thread; yields its URL
- `api_client` — a real `MealPlanClient` pointed at `live_server`
