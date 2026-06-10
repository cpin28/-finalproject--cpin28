"""mealplan GUI — a minimal tkinter window over the same client.

tkinter ships with Python, so there's no extra dependency. Same principle as the other
clients: it only renders data fetched through MealPlanClient.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from mealplan_client import MealPlanClient


class MealPlanGUI:
    def __init__(self, base_url: str | None = None):
        self.client = MealPlanClient(base_url or os.environ.get("MEALPLAN_URL", "http://127.0.0.1:8000"))
        self.root = tk.Tk()
        self.root.title("mealplan")
        self.root.geometry("560x420")

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text="Recipes", command=self.show_recipes).pack(side="left")
        ttk.Button(toolbar, text="Shopping list", command=self.show_shopping).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self.root, columns=("a", "b", "c"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.status = ttk.Label(self.root, text="")
        self.status.pack(fill="x", padx=8, pady=4)

    def _set_columns(self, headers: tuple[str, str, str]) -> None:
        for col, head in zip(("a", "b", "c"), headers):
            self.tree.heading(col, text=head)
        self.tree.delete(*self.tree.get_children())

    def show_recipes(self) -> None:
        self._set_columns(("id", "recipe", "servings"))
        try:
            for r in self.client.list_recipes():
                self.tree.insert("", "end", values=(r["id"], r["name"], r["servings"]))
            self.status.config(text="Recipes")
        except Exception as exc:
            self.status.config(text=f"Could not reach server: {exc}")

    def show_shopping(self) -> None:
        self._set_columns(("qty", "unit", "ingredient"))
        try:
            items = self.client.shopping_list()
            for it in items:
                self.tree.insert("", "end", values=(f"{it['quantity']:g}", it["unit"], it["name"]))
            self.status.config(text="Shopping list" if items else "Nothing to buy")
        except Exception as exc:
            self.status.config(text=f"Could not reach server: {exc}")

    def run(self) -> None:
        self.show_recipes()
        self.root.mainloop()


def main() -> None:
    MealPlanGUI().run()


if __name__ == "__main__":
    main()
