# Design decisions

Small, deliberate choices and the reasoning behind them — including what was left out.

## 1. Client–server with a shared client library

The clients could each call `httpx` directly, but then the wire protocol would be
duplicated three times. Instead `mealplan_client` is the single place that knows the
URLs and JSON shapes. Adding a fourth client is a presentation exercise only, and the
integration tests drive this same client, so they test the code real users run.

## 2. Repository pattern / one storage module

Only `db.py` imports `sqlite3`, and only `repository.py` writes SQL. Everything above
works with `schemas` objects. The payoff: storage is swappable, and the planning logic
can be tested with zero database setup.

## 3. Derived data is computed, never stored

Shopping lists and "can I make this?" are functions of the plan + recipes + pantry, so
storing them would invite staleness. `planner.py` recomputes them on request. They're
pure functions, which makes them the best-tested part of the system.

## 4. Units are opaque labels — for now

Combining "200 g flour" with "1 kg flour" needs unit conversion, which is a rabbit hole
(mass vs volume, cups, density). For this project, quantities combine **only when their
unit strings match**; otherwise they're tracked separately and conservatively assumed
*not* to cover each other.

This is intentionally a **seam, not a dead end**: every quantity in `planner.py` is
routed through `_canonical(quantity, unit)`, currently the identity function. Supporting
unit families later means implementing only that one function — the aggregation,
subtraction, and cook-check logic pick it up unchanged.

## 5. Ingredients are a shared canonical list

Recipes and the pantry reference ingredients by id rather than by free-text name, so
"flour" in a recipe and "flour" in the pantry are guaranteed to be the same thing. This
is what makes pantry subtraction reliable.

## 6. Fuzzy search and suggestions are pure logic, kept out of SQL

Recipe search could have stayed a SQL `LIKE`, but approximate matching (subsequence,
compactness ranking) doesn't express well in SQL and isn't unit-testable in isolation.
So `search.py` scores in Python over recipes the repository returns — same reasoning as
`planner`: pure functions, exhaustively testable, no database. "What can I make?"
(`planner.suggest_recipes`) is likewise derived from recipes + pantry, never stored.

## 7. SQLite + a connection per request

The API opens a short-lived connection per request (via a FastAPI dependency) and closes
it after. Simple, thread-safe, and fine at this scale; no pooling needed.
