# Requirements

## Purpose

A personal recipe and meal-planning tool. The user stores recipes, tracks what's in
their kitchen, plans meals for the week, and gets a shopping list for whatever the plan
needs that the pantry doesn't already cover.

## Functional requirements

1. **Recipes** — create, list, view, delete a recipe. A recipe has a name, optional
   description/instructions, a serving count, a prep time, and a list of ingredients
   with quantities and units.
2. **Ingredients** — a shared canonical list of ingredients, each with a default unit.
   Recipes and the pantry both reference ingredients by id.
3. **Pantry** — track on-hand quantity per ingredient. Setting an item is an upsert.
4. **Meal plan** — assign a recipe to a (date, meal type) slot, optionally overriding
   servings. List the plan, optionally filtered to a date range. Remove a slot.
5. **Shopping list** (derived) — for a date range, total the ingredients the planned
   meals need, subtract what the pantry holds, and list the remainder.
6. **Cook check** (derived) — for a recipe, report whether the pantry can cover it and,
   if not, which ingredients are missing.
7. **Fuzzy search** — find recipes by an approximate name match (exact > prefix >
   substring > subsequence), not just exact substrings.
8. **Pantry suggestions** (derived) — "what can I make?": rank recipes by how well the
   pantry covers them, fully-makeable first, then fewest missing ingredients.

## Non-functional requirements

- **Single source of truth**: one server owns the data; all clients go through its REST
  API. No client touches the database directly.
- **Multiple front ends**: a CLI, a TUI, and a GUI, all over the same client library.
- **Testable core**: the planning logic is pure and unit-tested without a database.
- **Local & dependency-light**: SQLite for storage; runs with `uv` and Python 3.12+.

## Out of scope (deliberately)

- User accounts / multi-user / auth.
- Nutrition data, external recipe import, or recipe scraping.
- Full unit conversion across families (see `design.md` — a seam is left for it).
- Real-time sync or a hosted deployment.
