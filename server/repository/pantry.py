"""SQL for pantry (on-hand) stock."""

from __future__ import annotations

import sqlite3

from .. import schemas


def set_pantry_item(conn: sqlite3.Connection, data: schemas.PantryItemInput) -> schemas.PantryItem:
    conn.execute(
        """INSERT INTO pantry_items (ingredient_id, quantity, unit) VALUES (?, ?, ?)
           ON CONFLICT(ingredient_id) DO UPDATE SET quantity = excluded.quantity, unit = excluded.unit""",
        (data.ingredient_id, data.quantity, data.unit),
    )
    conn.commit()
    name = conn.execute("SELECT name FROM ingredients WHERE id = ?", (data.ingredient_id,)).fetchone()["name"]
    return schemas.PantryItem(ingredient_id=data.ingredient_id, name=name, quantity=data.quantity, unit=data.unit)


def list_pantry(conn: sqlite3.Connection) -> list[schemas.PantryItem]:
    rows = conn.execute(
        """SELECT p.ingredient_id, i.name, p.quantity, p.unit
           FROM pantry_items p JOIN ingredients i ON i.id = p.ingredient_id
           ORDER BY i.name""",
    ).fetchall()
    return [schemas.PantryItem(**dict(r)) for r in rows]


def remove_pantry_item(conn: sqlite3.Connection, ingredient_id: int) -> bool:
    cur = conn.execute("DELETE FROM pantry_items WHERE ingredient_id = ?", (ingredient_id,))
    conn.commit()
    return cur.rowcount > 0
