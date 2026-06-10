"""SQLite connection + schema. The only module that knows we use SQLite.

Isolating connection/setup here keeps the storage choice swappable: the repository
talks to a `sqlite3.Connection`, and nothing above it imports `sqlite3` directly.
"""

from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingredients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    default_unit TEXT NOT NULL DEFAULT 'unit'
);

CREATE TABLE IF NOT EXISTS recipes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    instructions      TEXT NOT NULL DEFAULT '',
    servings          INTEGER NOT NULL DEFAULT 1,
    prep_time_minutes INTEGER NOT NULL DEFAULT 0,
    difficulty        TEXT NOT NULL DEFAULT 'beginner'
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id     INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity      REAL NOT NULL,
    unit          TEXT NOT NULL,
    PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS pantry_items (
    ingredient_id INTEGER PRIMARY KEY REFERENCES ingredients(id),
    quantity      REAL NOT NULL,
    unit          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS planned_meals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    servings  INTEGER
);

-- Directional ingredient substitutions: in a recipe that calls for `ingredient_id`,
-- you may use `substitute_id` instead, at `ratio` (substitute amount per unit of the
-- original) with a free-text `note`. The reverse swap, if valid, is a separate row.
CREATE TABLE IF NOT EXISTS substitutions (
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    substitute_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    ratio         REAL NOT NULL DEFAULT 1.0,
    note          TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (ingredient_id, substitute_id)
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight, idempotent migrations for databases created before a column existed.

    (A real project would use a migration tool; at this scale a guarded ALTER is enough.)
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(recipes)")}
    if "difficulty" not in cols:
        conn.execute("ALTER TABLE recipes ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'beginner'")
