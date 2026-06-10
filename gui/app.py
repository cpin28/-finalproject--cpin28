"""mealplan GUI (tkinter) — feature parity with the web client.

A ttk.Notebook with four tabs: Recipes (with a cook check), an editable Pantry, the
weekly Plan (add/remove), and the Shopping list. tkinter ships with Python, so there's
no extra dependency. Presentation only — all data comes through MealPlanClient.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from mealplan_client import MealPlanClient

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


class MealPlanGUI:
    def __init__(self, base_url: str | None = None):
        self.client = MealPlanClient(base_url or os.environ.get("MEALPLAN_URL", "http://127.0.0.1:8000"))
        self._recipes: dict[int, dict] = {}
        self._ingredients: dict[str, int] = {}   # "name" -> id
        self._recipe_names: dict[str, int] = {}  # "name" -> id

        self.root = tk.Tk()
        self.root.title("mealplan")
        self.root.geometry("720x520")

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=6)
        self._build_recipes()
        self._build_pantry()
        self._build_plan()
        self._build_shopping()

        self.status = ttk.Label(self.root, text="", anchor="w", foreground="#c2571a")
        self.status.pack(fill="x", padx=10, pady=(0, 6))

    # --- helpers ---
    def _safe(self, fn, *a, **k):
        try:
            return fn(*a, **k)
        except Exception as exc:
            messagebox.showerror("mealplan", str(exc))
            return None

    def _say(self, msg: str) -> None:
        self.status.config(text=msg)

    @staticmethod
    def _clear(tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())

    # --- Recipes tab ---
    def _build_recipes(self) -> None:
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Recipes")

        top = ttk.Frame(f)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="Search:").pack(side="left")
        self.recipe_search = ttk.Entry(top)
        self.recipe_search.pack(side="left", fill="x", expand=True, padx=4)
        self.recipe_search.bind("<KeyRelease>", lambda _e: self.load_recipes())

        body = ttk.Frame(f)
        body.pack(fill="both", expand=True)
        self.recipe_tree = ttk.Treeview(body, columns=("name", "servings"), show="headings", height=12)
        self.recipe_tree.heading("name", text="Recipe")
        self.recipe_tree.heading("servings", text="Servings")
        self.recipe_tree.column("servings", width=80, anchor="center")
        self.recipe_tree.pack(side="left", fill="both", expand=True)
        self.recipe_tree.bind("<<TreeviewSelect>>", self._on_recipe_select)

        self.recipe_detail = tk.Text(body, width=42, wrap="word", state="disabled", relief="flat", bg="#fafaf7")
        self.recipe_detail.pack(side="left", fill="both", padx=(8, 0))

    def _on_recipe_select(self, _e=None) -> None:
        sel = self.recipe_tree.selection()
        if not sel:
            return
        recipe_id = int(sel[0])
        r = self._recipes.get(recipe_id)
        check = self._safe(self.client.can_make, recipe_id)
        if not r or check is None:
            return
        badge = "✓ pantry has everything" if check["can_make"] else f"missing: {', '.join(check['missing'])}"
        lines = [f"{r['name']}  ({r['servings']} servings, {r['prep_time_minutes']}m)", badge, ""]
        if r["description"]:
            lines += [r["description"], ""]
        lines.append("Ingredients:")
        lines += [f"  - {i['quantity']:g} {i['unit']} {i['name']}" for i in r["ingredients"]]
        if r["instructions"]:
            lines += ["", "Instructions:", r["instructions"]]
        self.recipe_detail.config(state="normal")
        self.recipe_detail.delete("1.0", "end")
        self.recipe_detail.insert("1.0", "\n".join(lines))
        self.recipe_detail.config(state="disabled")

    def load_recipes(self) -> None:
        q = self.recipe_search.get().strip() or None
        recipes = self._safe(self.client.list_recipes, q)
        if recipes is None:
            return
        self._recipes = {r["id"]: r for r in recipes}
        self._recipe_names = {r["name"]: r["id"] for r in recipes}
        self._clear(self.recipe_tree)
        for r in recipes:
            self.recipe_tree.insert("", "end", iid=str(r["id"]), values=(r["name"], r["servings"]))
        if hasattr(self, "plan_recipe"):
            self.plan_recipe["values"] = list(self._recipe_names)

    # --- Pantry tab ---
    def _build_pantry(self) -> None:
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Pantry")

        form = ttk.Frame(f)
        form.pack(fill="x", pady=4)
        self.pantry_ingredient = ttk.Combobox(form, state="readonly", width=18)
        self.pantry_ingredient.pack(side="left")
        self.pantry_qty = ttk.Entry(form, width=8)
        self.pantry_qty.pack(side="left", padx=4)
        self.pantry_qty.insert(0, "")
        self.pantry_unit = ttk.Entry(form, width=8)
        self.pantry_unit.pack(side="left")
        ttk.Button(form, text="Set", command=self.set_pantry).pack(side="left", padx=4)
        ttk.Button(form, text="Remove selected", command=self.remove_pantry).pack(side="left")

        self.pantry_tree = ttk.Treeview(f, columns=("name", "qty", "unit"), show="headings")
        for col, txt, w in (("name", "Ingredient", 200), ("qty", "Qty", 80), ("unit", "Unit", 80)):
            self.pantry_tree.heading(col, text=txt)
            self.pantry_tree.column(col, width=w)
        self.pantry_tree.pack(fill="both", expand=True, pady=4)

    def load_pantry(self) -> None:
        pantry = self._safe(self.client.list_pantry)
        ingredients = self._safe(self.client.list_ingredients)
        if pantry is None or ingredients is None:
            return
        self._ingredients = {i["name"]: i["id"] for i in ingredients}
        self.pantry_ingredient["values"] = list(self._ingredients)
        self._clear(self.pantry_tree)
        for p in pantry:
            self.pantry_tree.insert("", "end", iid=str(p["ingredient_id"]),
                                    values=(p["name"], f"{p['quantity']:g}", p["unit"]))

    def set_pantry(self) -> None:
        name = self.pantry_ingredient.get()
        qty, unit = self.pantry_qty.get().strip(), self.pantry_unit.get().strip()
        if name not in self._ingredients or not qty or not unit:
            self._say("pick an ingredient and enter qty + unit")
            return
        if self._safe(self.client.set_pantry, self._ingredients[name], float(qty), unit) is not None:
            self.pantry_qty.delete(0, "end")
            self._say("pantry updated")
            self.load_pantry()

    def remove_pantry(self) -> None:
        sel = self.pantry_tree.selection()
        if not sel:
            self._say("select a pantry row to remove")
            return
        if self._safe(self.client.remove_pantry, int(sel[0])) is not None:
            self.load_pantry()

    # --- Plan tab ---
    def _build_plan(self) -> None:
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Weekly plan")

        form = ttk.Frame(f)
        form.pack(fill="x", pady=4)
        self.plan_date = ttk.Entry(form, width=12)
        self.plan_date.insert(0, "YYYY-MM-DD")
        self.plan_date.pack(side="left")
        self.plan_meal = ttk.Combobox(form, state="readonly", width=10, values=list(MEAL_TYPES))
        self.plan_meal.set("dinner")
        self.plan_meal.pack(side="left", padx=4)
        self.plan_recipe = ttk.Combobox(form, state="readonly", width=18)
        self.plan_recipe.pack(side="left")
        ttk.Button(form, text="Add", command=self.add_plan).pack(side="left", padx=4)
        ttk.Button(form, text="Remove selected", command=self.remove_plan).pack(side="left")

        self.plan_tree = ttk.Treeview(f, columns=("date", "meal", "recipe", "servings"), show="headings")
        for col, txt in (("date", "Date"), ("meal", "Meal"), ("recipe", "Recipe"), ("servings", "Servings")):
            self.plan_tree.heading(col, text=txt)
        self.plan_tree.pack(fill="both", expand=True, pady=4)

    def load_plan(self) -> None:
        plan = self._safe(self.client.list_plan)
        if plan is None:
            return
        self._clear(self.plan_tree)
        for m in plan:
            self.plan_tree.insert("", "end", iid=str(m["id"]),
                                  values=(m["date"], m["meal_type"], m["recipe_name"], m["servings"]))

    def add_plan(self) -> None:
        date, meal, recipe = self.plan_date.get().strip(), self.plan_meal.get(), self.plan_recipe.get()
        if not date or recipe not in self._recipe_names:
            self._say("enter a date and pick a recipe")
            return
        if self._safe(self.client.add_plan, date, meal, self._recipe_names[recipe]) is not None:
            self._say("added to plan")
            self.load_plan()

    def remove_plan(self) -> None:
        sel = self.plan_tree.selection()
        if not sel:
            self._say("select a planned meal to remove")
            return
        if self._safe(self.client.remove_plan, int(sel[0])) is not None:
            self.load_plan()

    # --- Shopping tab ---
    def _build_shopping(self) -> None:
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Shopping list")

        form = ttk.Frame(f)
        form.pack(fill="x", pady=4)
        ttk.Label(form, text="From").pack(side="left")
        self.shop_start = ttk.Entry(form, width=12)
        self.shop_start.pack(side="left", padx=4)
        ttk.Label(form, text="To").pack(side="left")
        self.shop_end = ttk.Entry(form, width=12)
        self.shop_end.pack(side="left", padx=4)
        ttk.Button(form, text="Generate", command=self.load_shopping).pack(side="left", padx=4)

        self.shop_tree = ttk.Treeview(f, columns=("qty", "unit", "name"), show="headings")
        for col, txt, w in (("qty", "Qty", 80), ("unit", "Unit", 80), ("name", "Ingredient", 220)):
            self.shop_tree.heading(col, text=txt)
            self.shop_tree.column(col, width=w)
        self.shop_tree.pack(fill="both", expand=True, pady=4)

    def load_shopping(self) -> None:
        start = self.shop_start.get().strip() or None
        end = self.shop_end.get().strip() or None
        items = self._safe(self.client.shopping_list, start, end)
        if items is None:
            return
        self._clear(self.shop_tree)
        for it in items:
            self.shop_tree.insert("", "end", values=(f"{it['quantity']:g}", it["unit"], it["name"]))
        self._say("nothing to buy — pantry covers the plan" if not items else "")

    # --- lifecycle ---
    def run(self) -> None:
        self.load_recipes()
        self.load_pantry()
        self.load_plan()
        self.root.mainloop()


def main() -> None:
    MealPlanGUI().run()


if __name__ == "__main__":
    main()
