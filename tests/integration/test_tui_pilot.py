"""Integration: drive the real TUI headlessly via Textual's run_test pilot.

This is the interactive-client analogue of test_client_against_server: it launches the
actual MealPlanTUI against a live server (seeded DB) and checks it loads data, renders the
suggestions tab, and fuzzy-searches — the behaviour a user would see, exercised without a
terminal. Run synchronously via asyncio.run so no pytest-asyncio plugin is needed.
"""

from __future__ import annotations

import asyncio

from textual.widgets import DataTable, Input

from migrations.seed import seed
from tui.app import MealPlanTUI


def test_tui_loads_data_and_fuzzy_searches(live_server, db_path):
    seed(db_path)  # populate the database the live server reads

    async def scenario():
        app = MealPlanTUI(live_server)
        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause()
            # initial load: 4 seeded recipes, and the suggestions tab is populated
            assert app.query_one("#recipe-table", DataTable).row_count == 4
            assert app.query_one("#suggest-table", DataTable).row_count == 4

            # fuzzy search: a gapped subsequence of "Pancakes" narrows to one row
            app.query_one("#recipe-search", Input).focus()
            await pilot.press("p", "n", "c", "k")
            await pilot.pause()
            table = app.query_one("#recipe-table", DataTable)
            assert table.row_count == 1
            assert table.get_row_at(0)[1] == "Pancakes"

    asyncio.run(scenario())
