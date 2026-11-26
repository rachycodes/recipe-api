from flask import Blueprint, g, jsonify, request
from ..extensions import cache
from ..models import Recipe
from ..services.recipe_service import (
    list_recipes_for_user,
    create_recipe_for_user,
    get_visible_recipe,
    get_owned_recipe,
    update_recipe_for_user,
    delete_recipe_for_user,
)
from .auth import require_auth, optional_auth
from ..utils import is_nonempty_str


# --- Configuration -------------------------------------------------

MAX_PAGE_SIZE = 100


# --- Blueprint -----------------------------------------------------

recipes_bp = Blueprint("recipes", __name__, url_prefix="/recipes")

# --- Helpers -------------------------------------------------------


def recipe_to_dict(row):
    """Serialize both SQLAlchemy objects and SQLite rows."""

    if isinstance(row, Recipe):
        return {
            "id": row.id,
            "user_id": row.user_id,
            "title": row.title,
            "ingredients": row.ingredients,
            "instructions": row.instructions,
            "is_public": bool(row.is_public),
        }

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }

# --- GET All Recipes -----------------------------------------------

@cache.cached(timeout=60)
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

    rows = list_recipes_for_user(g.user_id, limit, offset)

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

    # keep your existing validation...

    instructions = data.get("instructions", "")
    if not isinstance(instructions, str):
        return jsonify({
            "error": "instructions must be a string"
        }), 400

    is_public = data.get("is_public", True)

    row, error = create_recipe_for_user(
        g.user_id,
        data["title"],
        data["ingredients"],
        instructions,
        is_public,
    )

    if error == "integrity_error":
        return jsonify({
            "error": "could not create recipe (duplicate title?)"
        }), 409

    return jsonify(recipe_to_dict(row)), 201


# --- PATCH Update Recipe -------------------------------------------
# --- PATCH Update Recipe -------------------------------------------

@recipes_bp.patch("/<int:recipe_id>")
@require_auth
def update_recipe(recipe_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "a JSON body is required"
        }), 400

    if get_owned_recipe(recipe_id, g.user_id) is None:
        return jsonify({
            "error": "recipe not found"
        }), 404

    updates = {}

    for column in ("title", "ingredients"):
        if column in data:

            if not is_nonempty_str(data[column]):
                return jsonify({
                    "error": f"{column} must be a non-empty string"
                }), 400

            updates[column] = (
                data[column].strip()
                if column == "title"
                else data[column]
            )

    if "instructions" in data:
        if not isinstance(data["instructions"], str):
            return jsonify({
                "error": "instructions must be a string"
            }), 400

        updates["instructions"] = data["instructions"]

    if "is_public" in data:
        updates["is_public"] = bool(data["is_public"])

    if not updates:
        return jsonify({
            "error": "nothing to update"
        }), 400

    recipe, error = update_recipe_for_user(
        recipe_id,
        g.user_id,
        updates,
    )

    if error == "not_found":
        return jsonify({
            "error": "recipe not found"
        }), 404

    if error == "integrity_error":
        return jsonify({
            "error": "could not update recipe (duplicate title?)"
        }), 409

    return jsonify(recipe_to_dict(recipe)), 200

# --- DELETE Recipes -------------------------------------------------

@recipes_bp.delete("/<int:recipe_id>")
@require_auth
def delete_recipe(recipe_id):

    error = delete_recipe_for_user(
        recipe_id,
        g.user_id,
        getattr(g, "role", None),
    )

    if error == "not_found":
        return jsonify({
            "error": "recipe not found"
        }), 404

    if error == "forbidden":
        return jsonify({
            "error": "forbidden: you cannot delete this recipe"
        }), 403

    if error == "integrity_error":
        return jsonify({
            "error": "could not delete recipe"
        }), 409

    return "", 204