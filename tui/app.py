"""mealplan TUI (textual) — feature parity with the web client.

Four tabs: Recipes (with a "can I make this?" check), an editable Pantry, the weekly
Plan (add/remove meals), and the Shopping list. Like every client it owns presentation
only; all data flows through MealPlanClient.
"""

from __future__ import annotations

import os

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from mealplan_client import MealPlanClient

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


class MealPlanTUI(App):
    CSS = """
    DataTable { height: 1fr; }
    #recipe-detail { width: 1fr; padding: 0 1; border: round $primary; }
    .form { height: auto; padding: 1 0; }
    .form Input, .form Select { width: 20; margin-right: 1; }
    """
    BINDINGS = [("q", "quit", "Quit"), ("d", "remove_selected", "Remove selected")]

    def __init__(self, base_url: str | None = None):
        super().__init__()
        self.client = MealPlanClient(base_url or os.environ.get("MEALPLAN_URL", "http://127.0.0.1:8000"))
        self._recipes: dict[int, dict] = {}      # recipe id -> recipe
        self._pantry_rows: dict = {}             # DataTable row key -> ingredient_id
        self._plan_rows: dict = {}               # DataTable row key -> planned meal id

    # --- layout ---
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="recipes-tab"):
            with TabPane("Recipes", id="recipes-tab"):
                yield Input(placeholder="Fuzzy-search recipes…", id="recipe-search")
                with Horizontal():
                    yield DataTable(id="recipe-table", cursor_type="row")
                    yield Static("Select a recipe.", id="recipe-detail")
            with TabPane("Suggest", id="suggest-tab"):
                yield DataTable(id="suggest-table", cursor_type="row")
            with TabPane("Pantry", id="pantry-tab"):
                with Horizontal(classes="form"):
                    yield Select([], id="pantry-ingredient", prompt="ingredient", allow_blank=True)
                    yield Input(placeholder="qty", id="pantry-qty")
                    yield Input(placeholder="unit", id="pantry-unit")
                    yield Button("Set", id="pantry-set", variant="primary")
                yield DataTable(id="pantry-table", cursor_type="row")
            with TabPane("Plan", id="plan-tab"):
                with Horizontal(classes="form"):
                    yield Input(placeholder="YYYY-MM-DD", id="plan-date")
                    yield Select([(m, m) for m in MEAL_TYPES], id="plan-meal", value="dinner")
                    yield Select([], id="plan-recipe", prompt="recipe", allow_blank=True)
                    yield Button("Add", id="plan-add", variant="primary")
                yield DataTable(id="plan-table", cursor_type="row")
            with TabPane("Shopping", id="shop-tab"):
                with Horizontal(classes="form"):
                    yield Input(placeholder="start YYYY-MM-DD", id="shop-start")
                    yield Input(placeholder="end YYYY-MM-DD", id="shop-end")
                    yield Button("Generate", id="shop-gen", variant="primary")
                yield DataTable(id="shop-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#recipe-table", DataTable).add_columns("id", "recipe", "servings")
        self.query_one("#suggest-table", DataTable).add_columns("recipe", "status")
        self.query_one("#pantry-table", DataTable).add_columns("ingredient", "qty", "unit")
        self.query_one("#plan-table", DataTable).add_columns("date", "meal", "recipe", "servings")
        self.query_one("#shop-table", DataTable).add_columns("qty", "unit", "ingredient")
        self.refresh_recipes()
        self.refresh_suggestions()
        self.refresh_pantry()
        self.refresh_plan()

    # --- data loaders ---
    def _safe(self, fn, *a, **k):
        try:
            return fn(*a, **k)
        except Exception as exc:  # pragma: no cover - network/UI failure path
            self.notify(str(exc), severity="error")
            return None

    def refresh_recipes(self, query: str | None = None) -> None:
        # fuzzy search when there's a query, otherwise the full list
        recipes = self._safe(self.client.search_recipes, query) if query else self._safe(self.client.list_recipes)
        if recipes is None:
            return
        self._recipes = {r["id"]: r for r in recipes}
        table = self.query_one("#recipe-table", DataTable)
        table.clear()
        for r in recipes:
            table.add_row(str(r["id"]), r["name"], str(r["servings"]), key=str(r["id"]))
        # keep the plan tab's recipe picker populated with the full list (not the filtered one)
        if not query:
            self.query_one("#plan-recipe", Select).set_options([(r["name"], r["id"]) for r in recipes])

    def refresh_suggestions(self) -> None:
        suggestions = self._safe(self.client.suggest_recipes)
        if suggestions is None:
            return
        table = self.query_one("#suggest-table", DataTable)
        table.clear()
        for s in suggestions:
            status = ("✓ ready to cook" if s["can_make"]
                      else f"have {s['have_count']}/{s['need_count']} — missing: {', '.join(s['missing'])}")
            table.add_row(s["name"], status)

    def refresh_pantry(self) -> None:
        pantry = self._safe(self.client.list_pantry)
        ingredients = self._safe(self.client.list_ingredients)
        if pantry is None or ingredients is None:
            return
        self.query_one("#pantry-ingredient", Select).set_options([(i["name"], i["id"]) for i in ingredients])
        table = self.query_one("#pantry-table", DataTable)
        table.clear()
        self._pantry_rows = {}
        for p in pantry:
            key = f"pantry-{p['ingredient_id']}"
            table.add_row(p["name"], f"{p['quantity']:g}", p["unit"], key=key)
            self._pantry_rows[key] = p["ingredient_id"]

    def refresh_plan(self) -> None:
        plan = self._safe(self.client.list_plan)
        if plan is None:
            return
        table = self.query_one("#plan-table", DataTable)
        table.clear()
        self._plan_rows = {}
        for m in plan:
            key = f"plan-{m['id']}"
            table.add_row(m["date"], m["meal_type"], m["recipe_name"], str(m["servings"]), key=key)
            self._plan_rows[key] = m["id"]

    # --- events ---
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "recipe-search":
            self.refresh_recipes(event.value.strip() or None)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "recipe-table":
            self.show_recipe(int(event.row_key.value))

    def show_recipe(self, recipe_id: int) -> None:
        r = self._recipes.get(recipe_id)
        if not r:
            return
        check = self._safe(self.client.can_make, recipe_id)
        if check is None:
            return
        badge = "[green]✓ pantry has everything[/]" if check["can_make"] else f"[orange1]missing: {', '.join(check['missing'])}[/]"
        lines = [f"[b]{r['name']}[/b]  ({r['servings']} servings, {r['prep_time_minutes']}m)", badge, ""]
        if r["description"]:
            lines += [r["description"], ""]
        lines.append("[u]Ingredients[/u]")
        lines += [f"  • {i['quantity']:g} {i['unit']} {i['name']}" for i in r["ingredients"]]
        if r["instructions"]:
            lines += ["", "[u]Instructions[/u]", r["instructions"]]
        self.query_one("#recipe-detail", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pantry-set":
            self._set_pantry()
        elif event.button.id == "plan-add":
            self._add_plan()
        elif event.button.id == "shop-gen":
            self._generate_shopping()

    def _set_pantry(self) -> None:
        ing = self.query_one("#pantry-ingredient", Select).value
        qty = self.query_one("#pantry-qty", Input).value.strip()
        unit = self.query_one("#pantry-unit", Input).value.strip()
        if ing is Select.BLANK or not qty or not unit:
            self.notify("pick an ingredient and enter qty + unit", severity="warning")
            return
        if self._safe(self.client.set_pantry, int(ing), float(qty), unit) is not None:
            self.query_one("#pantry-qty", Input).value = ""
            self.notify("pantry updated")
            self.refresh_pantry()
            self.refresh_suggestions()

    def _add_plan(self) -> None:
        date = self.query_one("#plan-date", Input).value.strip()
        meal = self.query_one("#plan-meal", Select).value
        recipe = self.query_one("#plan-recipe", Select).value
        if not date or meal is Select.BLANK or recipe is Select.BLANK:
            self.notify("enter date and pick meal + recipe", severity="warning")
            return
        if self._safe(self.client.add_plan, date, meal, int(recipe)) is not None:
            self.notify("added to plan")
            self.refresh_plan()

    def _generate_shopping(self) -> None:
        start = self.query_one("#shop-start", Input).value.strip() or None
        end = self.query_one("#shop-end", Input).value.strip() or None
        items = self._safe(self.client.shopping_list, start, end)
        if items is None:
            return
        table = self.query_one("#shop-table", DataTable)
        table.clear()
        for it in items:
            table.add_row(f"{it['quantity']:g}", it["unit"], it["name"])
        if not items:
            self.notify("nothing to buy — pantry covers the plan")

    def action_remove_selected(self) -> None:
        """Remove the highlighted row on the Pantry or Plan tab."""
        active = self.query_one(TabbedContent).active
        if active == "pantry-tab":
            table = self.query_one("#pantry-table", DataTable)
            if table.row_count:
                key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                ing = self._pantry_rows.get(key.value)
                if ing is not None and self._safe(self.client.remove_pantry, ing) is not None:
                    self.refresh_pantry()
                    self.refresh_suggestions()
        elif active == "plan-tab":
            table = self.query_one("#plan-table", DataTable)
            if table.row_count:
                key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                mid = self._plan_rows.get(key.value)
                if mid is not None and self._safe(self.client.remove_plan, mid) is not None:
                    self.refresh_plan()


def main() -> None:
    MealPlanTUI().run()


if __name__ == "__main__":
    main()
