import sqlite3
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"]
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(exception=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db(database):
    """Create tables if missing and migrate older databases."""

    db = sqlite3.connect(database)
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL DEFAULT '',
            is_public INTEGER NOT NULL DEFAULT 1
        );
        """
    )

    # Add user_id to older recipe tables
    columns = [
        r[1] for r in db.execute("PRAGMA table_info(recipes)")
    ]

    if "user_id" not in columns:
        db.execute(
            "ALTER TABLE recipes ADD COLUMN user_id INTEGER REFERENCES users(id)"
        )

    # Add role to older user tables
    user_columns = [
        r[1] for r in db.execute("PRAGMA table_info(users)")
    ]

    if "role" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
        )

    db.commit()
    db.close()