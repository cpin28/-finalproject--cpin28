# Refactoring log

This project demonstrates refactoring as a **process**: taking working code and
improving its structure *without changing its behavior*. Each refactor below is a single
focused commit with a clear before → after, and in every case the existing test suite was
left **completely untouched and still passed** — that unchanged-tests-still-green property
is the evidence the behavior was preserved.

Run `uv run pytest` at any of these commits to verify: 22 passing.

---

## Refactor 1 — Split the monolithic API into per-resource routers

**Commit:** `189d525` · `server/api.py` → `server/routers/` + `server/deps.py`

### Before
Every HTTP route lived inside a single ~135-line `create_app()` function in `api.py`.
The function mixed three unrelated concerns: app setup, the connection dependency, and
the route handlers for all five resources (ingredients, recipes, pantry, plan, shopping).
Finding "the pantry routes" meant scrolling through everything.

### After
- `server/routers/` — one `APIRouter` module per resource: `ingredients.py`, `recipes.py`,
  `pantry.py`, `plan.py`, `shopping.py`.
- `server/deps.py` — the shared per-request connection dependency, extracted so the routers
  can import it without importing the app module (which would be a circular import).
- `server/api.py` — now ~45 lines of pure **assembly**: create the app, init the DB,
  `include_router(...)` for each module, serve the web client.

### Modularity gained
- Each resource's routes are isolated, named, and independently navigable.
- Adding a resource is a new router module plus one `include_router` line — no edits to a
  giant shared function.
- Assembly is separated from routing, so `api.py` reads as a table of contents.

### Behavior preserved
All URL paths, status codes, and response models are identical. The 22 unit/contract/
integration tests were not modified and still pass.

---

## Refactor 2 — Split the repository into a per-entity package

**Commit:** `e97a3dd` · `server/repository.py` → `server/repository/`

### Before
All SQL for four entities sat in one ~190-line `repository.py`: ingredient CRUD, the
recipe queries (including the ingredient-name join), pantry upsert/list/delete, and the
meal-plan queries — all in one file.

### After
- `server/repository/` package with one module per entity: `ingredients.py`, `recipes.py`,
  `pantry.py`, `plan.py`.
- `__init__.py` re-exports every function, so the **public surface is unchanged** — callers
  still write `repository.create_recipe(...)`. No router, seed script, or test changed.
- The single cross-entity dependency (`plan` needs `recipes.get_recipe` to validate a recipe
  when scheduling a meal) is now an explicit `from .recipes import get_recipe` — the coupling
  is documented instead of implicit.

### Modularity gained
- Each entity's SQL is in its own focused file; the recipe join logic no longer sits next to
  unrelated pantry code.
- The previously-hidden coupling between plan and recipes is now visible as an import.
- New entities get their own module rather than growing one ever-larger file.

### Behavior preserved
The re-export keeps the exact `repository.<function>` API. The 22 tests were not modified
and still pass.

---

## Why the tests didn't change

Both refactors are deliberately **structure-only**. The test suite targets *behavior* —
HTTP contracts, repository round-trips, planner logic — not internal module layout. So the
fact that the same tests pass before and after is precisely what proves each refactor was
safe. This is the practical payoff of the layered architecture and the three-level test
strategy described in [`architecture.md`](architecture.md) and [`testing.md`](testing.md).
