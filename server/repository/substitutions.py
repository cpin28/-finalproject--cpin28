"""SQL for directional ingredient substitutions."""

from __future__ import annotations

import sqlite3
from collections import defaultdict

from .. import schemas


def _row_to_substitution(conn: sqlite3.Connection, ingredient_id: int, substitute_id: int,
                         ratio: float, note: str) -> schemas.Substitution:
    names = dict(conn.execute(
        "SELECT id, name FROM ingredients WHERE id IN (?, ?)", (ingredient_id, substitute_id)
    ).fetchall())
    return schemas.Substitution(
        ingredient_id=ingredient_id, ingredient_name=names.get(ingredient_id, ""),
        substitute_id=substitute_id, substitute_name=names.get(substitute_id, ""),
        ratio=ratio, note=note,
    )


def create_substitution(conn: sqlite3.Connection, data: schemas.SubstitutionInput) -> schemas.Substitution:
    conn.execute(
        """INSERT INTO substitutions (ingredient_id, substitute_id, ratio, note) VALUES (?, ?, ?, ?)
           ON CONFLICT(ingredient_id, substitute_id) DO UPDATE SET ratio = excluded.ratio, note = excluded.note""",
        (data.ingredient_id, data.substitute_id, data.ratio, data.note),
    )
    conn.commit()
    return _row_to_substitution(conn, data.ingredient_id, data.substitute_id, data.ratio, data.note)


def list_substitutions(conn: sqlite3.Connection) -> list[schemas.Substitution]:
    rows = conn.execute(
        """SELECT s.ingredient_id, i.name AS ingredient_name,
                  s.substitute_id, j.name AS substitute_name, s.ratio, s.note
           FROM substitutions s
           JOIN ingredients i ON i.id = s.ingredient_id
           JOIN ingredients j ON j.id = s.substitute_id
           ORDER BY i.name, j.name""",
    ).fetchall()
    return [schemas.Substitution(**dict(r)) for r in rows]


def substitutions_map(conn: sqlite3.Connection) -> dict[int, list[schemas.Substitution]]:
    """ingredient_id -> the substitutes that may replace it (for the planner)."""
    by_ingredient: dict[int, list[schemas.Substitution]] = defaultdict(list)
    for sub in list_substitutions(conn):
        by_ingredient[sub.ingredient_id].append(sub)
    return dict(by_ingredient)


def delete_substitution(conn: sqlite3.Connection, ingredient_id: int, substitute_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM substitutions WHERE ingredient_id = ? AND substitute_id = ?",
        (ingredient_id, substitute_id),
    )
    conn.commit()
    return cur.rowcount > 0
