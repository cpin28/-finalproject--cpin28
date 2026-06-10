# Mealplan

> A recipe and meal-planning application built as a course capstone — and a case study in
> disciplined, AI-assisted ("vibe coding") development.

**Mealplan** lets you store recipes, track what's in your kitchen, plan the week's meals,
and generate a shopping list for exactly what the plan needs but the pantry doesn't already
cover. It answers the two questions a home cook actually asks — *"what can I make right
now?"* and *"what do I need to buy?"* — and it does so over four interchangeable front ends
sharing one tested core.

---

## Highlights

- **Client–server architecture** — a single SQLite-backed REST API (FastAPI) with **four
  front ends** at feature parity: a scripting CLI, an interactive terminal UI (Textual), a
  desktop GUI (tkinter), and a browser web client — all driven through one shared HTTP
  client library.
- **A pure planning core** — shopping lists, cook checks, suggestions, and unit conversion
  are pure functions over typed models, with no database or I/O, which makes the most
  important logic the easiest to test.
- **Substitution-aware planning** — recipes can declare ingredient substitutes; the planner
  surfaces recipes you can cook *with a swap* ("out of butter? you have oil"), not just the
  ones you can cook outright.
- **Built test-first** — 80+ tests across unit, contract, and integration layers, plus a
  documented refactoring log showing structure-only changes made with the suite green
  throughout.

---

## Quick start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                                      # install dependencies into .venv

# (optional) seed a small demo database: ingredients, recipes, pantry, a plan, substitutions
uv run python -m migrations.seed mealplan.db

# (optional) load the catalogue of 100 ready-made "easy" recipes
uv run python -m migrations.easy_recipes mealplan.db

# start the API server (reads $MEALPLAN_DB, default: mealplan.db)
MEALPLAN_DB=mealplan.db uv run mealplan-server
```

With the server running, choose any front end:

```bash
uv run mealplan recipes                                       # CLI
uv run mealplan shopping-list --start 2026-06-10 --end 2026-06-16
uv run mealplan-tui                                           # terminal UI (Textual)
uv run mealplan-gui                                           # desktop GUI (tkinter)
```

…or open **http://127.0.0.1:8000/** for the **web client**. Interactive API documentation
(Swagger UI) is served at **`/docs`**.

---

## Features

| Capability       | What it does                                                                        |
|------------------|-------------------------------------------------------------------------------------|
| **Recipes**      | Ingredients, servings, prep time, instructions, and a difficulty tier.              |
| **Pantry**       | Track what you have on hand, per ingredient, in real units.                         |
| **Weekly plan**  | Assign recipes to date + meal-type slots; add and remove meals.                     |
| **Shopping list**| Totals the plan's ingredients, subtracts the pantry, and lists only what's left.    |
| **Cook check**   | *"Can I make this right now?"* — with the exact ingredients still missing.          |
| **Substitutions**| Register directional ingredient swaps; the cook check and suggestions become swap-aware. |
| **Fuzzy search** | Find recipes by approximate name (exact › prefix › substring › subsequence).         |
| **Suggestions**  | *"What can I make?"* — recipes ranked makeable › makeable-with-a-substitution › fewest missing. |

Unit handling is a first-class concern: quantities convert within mass (`g`/`kg`) and volume
(`ml`/`l`/`tsp`/`tbsp`/`cup`) families, so a pantry's `0.3 kg` of flour correctly offsets a
`500 g` requirement. All four clients reach parity on the interactive features; the CLI adds
scriptable one-off commands.

---

## Architecture

```
server/                REST API (FastAPI + SQLite)
  api.py               app factory + router registration
  routers/             one module per resource (recipes, pantry, plan, shopping, substitutions, …)
  repository/          one module per resource: all the SQL, behind a small data-access layer
  planner.py           pure planning logic — shopping list, cook check, suggestions, unit conversion
  schemas.py           Pydantic models shared across every layer (the data contract)
  search.py            fuzzy recipe ranking
  db.py / deps.py      connection + schema, FastAPI dependencies
  main.py              uvicorn entry point
mealplan_client/       shared HTTP client used by every Python front end
cli/  tui/  gui/        the three Python clients (argparse, Textual, tkinter)
static/                browser web client (HTML/CSS/JS), served at /
migrations/            demo seed + the 100-recipe catalogue loader
tests/                 unit · contract · integration
docs/                  requirements, architecture, design, test plan, refactoring log, diagrams
```

The dependency direction is one-way: **front ends → client library → HTTP → server →
repository → database.** The planner sits to the side as pure logic that the server calls
but never depends on infrastructure, which is what keeps it trivially testable.

See [`docs/architecture.md`](docs/architecture.md) for module-level detail and Mermaid
diagrams, and [`docs/design.md`](docs/design.md) for the decisions and trade-offs.

---

## Testing

```bash
uv run pytest          # unit + contract + integration
```

Coverage is layered to match the architecture:

- **Unit** — the planning core in isolation (scaling, aggregation, unit conversion,
  substitution ranking) with no database or HTTP.
- **Contract** — the HTTP API's status codes and response shapes, pinning the wire contract
  every client depends on.
- **Integration** — the real client library driving the real server over a real socket, plus
  headless smoke tests of the TUI and GUI.

The full test strategy, including a test-pyramid diagram, lives in
[`docs/testing.md`](docs/testing.md).

---

## How it was built

This project was developed for a **vibe-coding course** — building software by directing an
AI coding assistant — and it treats "vibe coding" as an *engineering discipline*, not a
shortcut. The workflow that produced it:

- **Spec-first.** Requirements, architecture, and design were written up front in
  [`docs/`](docs/) and used to steer implementation, rather than reverse-engineered after.
- **Test-driven.** Features were added red-first: a failing test describing the behavior,
  then the implementation that makes it pass (visible in the commit history, e.g. the unit
  conversion and substitution work).
- **Refactored deliberately.** Two structure-only refactors — splitting the monolithic
  repository and router modules into per-resource packages — were performed with the suite
  green throughout, and are narrated in [`docs/refactoring.md`](docs/refactoring.md).
- **Reviewable history.** Each commit is a single coherent change with an explanatory
  message, so the *process* is as legible as the result.

The takeaway: AI assistance accelerates the typing, but the architecture, the tests, and the
discipline are what make the codebase one you'd be comfortable maintaining.
