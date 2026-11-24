
import sqlite3

from flask import Blueprint, g, jsonify, request

from .db import get_db
from .auth import require_auth, optional_auth
from .utils import is_nonempty_str


# --- Configuration -------------------------------------------------

MAX_PAGE_SIZE = 100


# --- Blueprint -----------------------------------------------------

recipes_bp = Blueprint("recipes", __name__, url_prefix="/recipes")

# --- Helpers -------------------------------------------------------

def recipe_to_dict(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


def get_visible_recipe(recipe_id):
    """A recipe is visible if public or owned by the current user."""

    return get_db().execute(
        """
        SELECT * FROM recipes
        WHERE id = ? AND (is_public = 1 OR user_id = ?)
        """,
        (recipe_id, g.user_id),
    ).fetchone()


def get_owned_recipe(recipe_id):
    return get_db().execute(
        """
        SELECT * FROM recipes
        WHERE id = ? AND user_id = ?
        """,
        (recipe_id, g.user_id),
    ).fetchone()


def get_recipe_if_owner_or_admin(recipe_id):
    db = get_db()

    recipe = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,),
    ).fetchone()

    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    is_owner = recipe["user_id"] == g.user_id
    is_admin = getattr(g, "role", None) == "admin"

    if not (is_owner or is_admin):
        return jsonify({
            "error": "forbidden: you cannot delete this recipe"
        }), 403

    return recipe


# --- GET All Recipes -----------------------------------------------

@recipes_bp.get("/")
@require_auth
def list_recipes():
    try:
        limit = min(
            int(request.args.get("limit", 20)),
            MAX_PAGE_SIZE,
        )
        offset = int(request.args.get("offset", 0))

    except ValueError:
        return jsonify({
            "error": "limit and offset must be integers"
        }), 400

    if limit < 1 or offset < 0:
        return jsonify({
            "error": "limit must be >= 1 and offset >= 0"
        }), 400

    rows = get_db().execute(
        """
        SELECT * FROM recipes
        WHERE is_public = 1 OR user_id = ?
        ORDER BY id LIMIT ? OFFSET ?
        """,
        (g.user_id, limit, offset),
    ).fetchall()

    return jsonify([recipe_to_dict(row) for row in rows])


# --- GET Single Recipe ---------------------------------------------

@recipes_bp.get("/<int:recipe_id>")
@optional_auth
def get_recipe(recipe_id):
    row = get_visible_recipe(recipe_id)

    if row is None:
        return jsonify({
            "error": "recipe not found"
        }), 404

    return jsonify(recipe_to_dict(row))


# --- POST Create Recipe --------------------------------------------

@recipes_bp.post("/")
@require_auth
def create_recipe():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("title"))
        or not is_nonempty_str(data.get("ingredients"))
    ):
        return jsonify({
            "error": "title and ingredients are required strings"
        }), 400

    instructions = data.get("instructions", "")

    if not isinstance(instructions, str):
        return jsonify({
            "error": "instructions must be a string"
        }), 400

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
                g.user_id,
                data["title"].strip(),
                data["ingredients"],
                instructions,
                1 if data.get("is_public", True) else 0,
            ),
        )

        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()

        return jsonify({
            "error": "could not create recipe (duplicate title?)"
        }), 409

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()

    return jsonify(recipe_to_dict(row)), 201


# --- PATCH Update Recipe -------------------------------------------

@recipes_bp.patch("/<int:recipe_id>")
@require_auth
def update_recipe(recipe_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "a JSON body is required"
        }), 400

    if get_owned_recipe(recipe_id) is None:
        return jsonify({
            "error": "recipe not found"
        }), 404

    fields = []
    values = []

    for column in ("title", "ingredients"):
        if column in data:

            if not is_nonempty_str(data[column]):
                return jsonify({
                    "error": f"{column} must be a non-empty string"
                }), 400

            fields.append(f"{column} = ?")

            values.append(
                data[column].strip()
                if column == "title"
                else data[column]
            )

    if "instructions" in data:
        if not isinstance(data["instructions"], str):
            return jsonify({
                "error": "instructions must be a string"
            }), 400

        fields.append("instructions = ?")
        values.append(data["instructions"])

    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)

    if not fields:
        return jsonify({
            "error": "nothing to update"
        }), 400

    values.extend([recipe_id, g.user_id])

    db = get_db()

    try:
        db.execute(
            f"""
            UPDATE recipes
            SET {', '.join(fields)}
            WHERE id = ? AND user_id = ?
            """,
            values,
        )

        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()

        return jsonify({
            "error": "could not update recipe (duplicate title?)"
        }), 409

    return jsonify(
        recipe_to_dict(get_owned_recipe(recipe_id))
    )


# --- DELETE Recipe -------------------------------------------------

@recipes_bp.delete("/<int:recipe_id>")
@require_auth
def delete_recipe(recipe_id):
    result = get_recipe_if_owner_or_admin(recipe_id)

    if not isinstance(result, sqlite3.Row):
        return result

    db = get_db()

    db.execute(
        "DELETE FROM recipes WHERE id = ?",
        (recipe_id,),
    )

    db.commit()

    return "", 204
