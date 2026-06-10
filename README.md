# mealplan

A personal **recipe & meal-planner**. Store recipes, track what's in your kitchen, plan
the week's meals, and get a shopping list for whatever the plan needs that the pantry
doesn't already cover.

Built as a small **client–server** app: one SQLite-backed REST server, four front ends
(CLI, TUI, GUI, and a browser web UI) over a shared client library, and a fully tested
planning core.

## Quick start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                              # install deps into .venv

# seed a demo database (ingredients, a few recipes, pantry stock, a plan)
uv run python -m migrations.seed mealplan.db

# run the server (reads $MEALPLAN_DB, default mealplan.db)
MEALPLAN_DB=mealplan.db uv run mealplan-server

# in another terminal, use a client:
uv run mealplan recipes
uv run mealplan shopping-list --start 2026-06-10 --end 2026-06-16
uv run mealplan-tui                  # textual TUI
uv run mealplan-gui                  # tkinter GUI
```

Then open **http://127.0.0.1:8000/** in a browser for the **web UI**. (The API's Swagger
docs are at `/docs`.)

All four clients are at feature parity: browse/search recipes with a "can I make this?"
check, view and **edit** the pantry, build the weekly plan (add/remove meals), and
generate the shopping list. The CLI additionally scripts one-off actions; the TUI, GUI,
and web UI are interactive. In the TUI, press `d` to remove the highlighted pantry/plan
row; the GUI and web UI have explicit remove buttons.

## What it does

- **Recipes** with ingredients, servings, prep time, instructions.
- **Pantry** tracking — what you have on hand, per ingredient.
- **Weekly plan** — assign recipes to date + meal-type slots.
- **Shopping list** — totals the plan's ingredients, subtracts the pantry, lists the rest.
- **Cook check** — "can I make this right now?" with the missing ingredients.

## Layout

```
server/            REST server (FastAPI + SQLite)
  api.py           routes        planner.py   shopping-list / cook-check logic
  repository.py    all the SQL   schemas.py   shared data models
  db.py            connection    main.py      uvicorn entry
mealplan_client/   shared HTTP client used by every Python front end
cli/  tui/  gui/    the three Python clients
static/            web UI (HTML/CSS/JS) served by the server at /
migrations/        seed script
tests/             unit / contract / integration
docs/              requirements, architecture, design, testing, diagrams
```

## Tests

```bash
uv run pytest          # unit + contract + integration
```

See [`docs/`](docs/) for requirements, architecture, design rationale, and the test plan.
