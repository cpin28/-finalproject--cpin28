"""mealplan TUI — browse recipes and this week's shopping list.

Like the CLI, it's a pure client: all data comes from MealPlanClient. The TUI owns
*presentation* only, which keeps the UI swappable without touching the server.
"""

from __future__ import annotations

import os

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Static

from mealplan_client import MealPlanClient


class MealPlanTUI(App):
    BINDINGS = [
        ("r", "show_recipes", "Recipes"),
        ("s", "show_shopping", "Shopping list"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, base_url: str | None = None):
        super().__init__()
        self.client = MealPlanClient(base_url or os.environ.get("MEALPLAN_URL", "http://127.0.0.1:8000"))

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DataTable(id="table")
            yield Static("", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.action_show_recipes()

    def action_show_recipes(self) -> None:
        table = self.query_one("#table", DataTable)
        table.clear(columns=True)
        table.add_columns("id", "recipe", "servings")
        try:
            for r in self.client.list_recipes():
                table.add_row(str(r["id"]), r["name"], str(r["servings"]))
            self.query_one("#detail", Static).update("Recipes — press [b]s[/b] for the shopping list.")
        except Exception as exc:  # pragma: no cover - network failure path
            self.query_one("#detail", Static).update(f"[red]Could not reach server:[/red] {exc}")

    def action_show_shopping(self) -> None:
        table = self.query_one("#table", DataTable)
        table.clear(columns=True)
        table.add_columns("qty", "unit", "ingredient")
        try:
            items = self.client.shopping_list()
            for it in items:
                table.add_row(f"{it['quantity']:g}", it["unit"], it["name"])
            note = "Shopping list for all planned meals." if items else "Nothing to buy."
            self.query_one("#detail", Static).update(note)
        except Exception as exc:  # pragma: no cover
            self.query_one("#detail", Static).update(f"[red]Could not reach server:[/red] {exc}")


def main() -> None:
    MealPlanTUI().run()


if __name__ == "__main__":
    main()
