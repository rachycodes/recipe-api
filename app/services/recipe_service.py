import sqlite3
from ..db import get_db


def list_recipes_for_user(user_id: int, limit: int, offset: int):
    """Retrieve public recipes and recipes owned by the user."""

    db = get_db()

    rows = db.execute(
        """
        SELECT * FROM recipes
        WHERE is_public = 1 OR user_id = ?
        ORDER BY id LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ).fetchall()

    return rows

def create_recipe_for_user(user_id: int, title: str, ingredients: str,
                           instructions: str, is_public: bool):
    db = get_db()
    try:
        cur = db.execute(
            """
            INSERT INTO recipes (
                user_id,
                title,
                ingredients,
                instructions,
                is_public
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title.strip(),
                ingredients,
                instructions,
                1 if is_public else 0,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        # signal duplicate / integrity problem
        return None, "integrity_error"

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return row, None