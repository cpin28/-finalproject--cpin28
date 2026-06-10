"""`mealplan` CLI — a thin terminal client over MealPlanClient.

Subcommands map one-to-one onto API resources. Output is plain text so it stays easy
to read and easy to assert on in integration tests.
"""

from __future__ import annotations

import argparse
import os
import sys

from mealplan_client import MealPlanClient


def _client(args: argparse.Namespace) -> MealPlanClient:
    base = args.url or os.environ.get("MEALPLAN_URL", "http://127.0.0.1:8000")
    return MealPlanClient(base)


def cmd_ingredients(client: MealPlanClient, args: argparse.Namespace) -> int:
    if args.add:
        ing = client.create_ingredient(args.add, args.unit or "unit")
        print(f"added #{ing['id']} {ing['name']} ({ing['default_unit']})")
        return 0
    for i in client.list_ingredients():
        print(f"{i['id']:>3}  {i['name']} ({i['default_unit']})")
    return 0


def cmd_recipes(client: MealPlanClient, args: argparse.Namespace) -> int:
    recipes = client.search_recipes(args.search) if args.search else client.list_recipes()
    for r in recipes:
        print(f"{r['id']:>3}  {r['name']}  ({r['servings']} servings, {r['prep_time_minutes']}m)")
    return 0


def cmd_suggestions(client: MealPlanClient, args: argparse.Namespace) -> int:
    suggestions = client.suggest_recipes(args.limit)
    for s in suggestions:
        if s["can_make"]:
            print(f"✓ {s['name']}  — ready to cook")
        else:
            print(f"  {s['name']}  — have {s['have_count']}/{s['need_count']}, missing: {', '.join(s['missing'])}")
    return 0


def cmd_recipe(client: MealPlanClient, args: argparse.Namespace) -> int:
    r = client.get_recipe(args.id)
    print(f"# {r['name']}  ({r['servings']} servings)")
    if r["description"]:
        print(r["description"])
    print("\nIngredients:")
    for ri in r["ingredients"]:
        print(f"  - {ri['quantity']:g} {ri['unit']} {ri['name']}")
    if r["instructions"]:
        print("\nInstructions:\n" + r["instructions"])
    return 0


def cmd_pantry(client: MealPlanClient, args: argparse.Namespace) -> int:
    if args.set is not None:
        item = client.set_pantry(args.set, args.qty, args.unit or "unit")
        print(f"pantry: {item['name']} = {item['quantity']:g} {item['unit']}")
        return 0
    for p in client.list_pantry():
        print(f"{p['quantity']:g} {p['unit']:<6} {p['name']}")
    return 0


def cmd_plan(client: MealPlanClient, args: argparse.Namespace) -> int:
    if args.add:
        date, meal_type, recipe_id = args.add
        meal = client.add_plan(date, meal_type, int(recipe_id))
        print(f"planned #{meal['id']}: {meal['date']} {meal['meal_type']} -> {meal['recipe_name']}")
        return 0
    for m in client.list_plan(args.start, args.end):
        print(f"{m['date']}  {m['meal_type']:<9} {m['recipe_name']} (x{m['servings']})")
    return 0


def cmd_shopping(client: MealPlanClient, args: argparse.Namespace) -> int:
    items = client.shopping_list(args.start, args.end)
    if not items:
        print("Nothing to buy — pantry covers the plan. 🎉")
        return 0
    print("Shopping list:")
    for it in items:
        print(f"  [ ] {it['quantity']:g} {it['unit']} {it['name']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mealplan", description="Recipe & meal-planner client")
    p.add_argument("--url", help="server base URL (default: $MEALPLAN_URL or localhost:8000)")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("ingredients", help="list or add ingredients")
    pi.add_argument("--add", metavar="NAME", help="add an ingredient")
    pi.add_argument("--unit", help="default unit for --add")
    pi.set_defaults(func=cmd_ingredients)

    pr = sub.add_parser("recipes", help="list or fuzzy-search recipes")
    pr.add_argument("--search", help="fuzzy-match recipes by name")
    pr.set_defaults(func=cmd_recipes)

    psug = sub.add_parser("suggestions", help="recipes you can make (or nearly make) from your pantry")
    psug.add_argument("--limit", type=int, default=10, help="max suggestions")
    psug.set_defaults(func=cmd_suggestions)

    prc = sub.add_parser("recipe", help="show one recipe")
    prc.add_argument("id", type=int)
    prc.set_defaults(func=cmd_recipe)

    pp = sub.add_parser("pantry", help="list or set pantry items")
    pp.add_argument("--set", type=int, metavar="INGREDIENT_ID", help="ingredient id to set")
    pp.add_argument("--qty", type=float, default=0.0, help="quantity for --set")
    pp.add_argument("--unit", help="unit for --set")
    pp.set_defaults(func=cmd_pantry)

    pl = sub.add_parser("plan", help="list or add planned meals")
    pl.add_argument("--add", nargs=3, metavar=("DATE", "MEAL_TYPE", "RECIPE_ID"), help="add a planned meal")
    pl.add_argument("--start", help="ISO start date filter")
    pl.add_argument("--end", help="ISO end date filter")
    pl.set_defaults(func=cmd_plan)

    ps = sub.add_parser("shopping-list", help="show shopping list for a date range")
    ps.add_argument("--start", help="ISO start date")
    ps.add_argument("--end", help="ISO end date")
    ps.set_defaults(func=cmd_shopping)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with _client(args) as client:
        return args.func(client, args)


if __name__ == "__main__":
    sys.exit(main())
