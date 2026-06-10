"""Integration: drive the real tkinter GUI against a live server.

tkinter needs a display, which a headless CI may not have — so the test skips cleanly
when `Tk()` can't initialise. Where a display exists, it constructs the real GUI, runs the
load methods (what `run()` does minus the blocking mainloop), and checks the widgets
populate and fuzzy search narrows the list.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from gui.app import MealPlanGUI
from migrations.seed import seed


def _gui(url: str) -> MealPlanGUI:
    try:
        return MealPlanGUI(url)
    except tk.TclError as exc:  # pragma: no cover - headless environment
        pytest.skip(f"tkinter has no display: {exc}")


def test_gui_loads_data_and_fuzzy_searches(live_server, db_path):
    seed(db_path)  # populate the database the live server reads
    gui = _gui(live_server)
    try:
        gui.load_recipes()
        gui.load_suggestions()
        gui.load_pantry()
        gui.load_plan()

        assert len(gui.recipe_tree.get_children()) == 4
        assert len(gui.suggest_tree.get_children()) == 4
        assert len(gui.pantry_tree.get_children()) == 5
        assert len(gui.plan_tree.get_children()) == 3

        # fuzzy search: a gapped subsequence of "Chicken & Rice" narrows to one row
        gui.recipe_search.insert(0, "chkn")
        gui.load_recipes()
        names = [gui.recipe_tree.item(i)["values"][0] for i in gui.recipe_tree.get_children()]
        assert names == ["Chicken & Rice"]
    finally:
        gui.root.destroy()
