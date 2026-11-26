
from sqlalchemy import or_
from flask import g
from ..extensions import db
from ..models import Recipe
from sqlalchemy.exc import IntegrityError

def list_recipes_for_user(user_id: int, limit: int, offset: int):
    """Retrieve public recipes and recipes owned by the user."""

    query = Recipe.query

    # Filter by visibility or ownership
    query = query.filter(
        or_(
            Recipe.is_public == 1,
            Recipe.user_id == user_id
        )
    )

    # Preserve original ordering
    query = query.order_by(Recipe.id.asc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Return a list of Recipe objects
    return query.all()

def get_visible_recipe(recipe_id: int):
    query = Recipe.query

    query = query.filter(
        Recipe.id == recipe_id,
        or_(
            Recipe.is_public == 1,
            Recipe.user_id == g.user_id,
        ),
    )

    return query.one_or_none()



def create_recipe_for_user(
    user_id: int,
    title: str,
    ingredients: str,
    instructions: str,
    is_public: int
):
    """Create a new recipe."""

    recipe = Recipe(
        user_id=user_id,
        title=title.strip(),
        ingredients=ingredients,
        instructions=instructions,
        is_public=1 if is_public else 0
    )

    try:
        db.session.add(recipe)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return None, "integrity_error"

    return recipe, None
def update_recipe_for_user(
    recipe_id: int,
    user_id: int,
    updates: dict
):
    """Update a recipe owned by the user."""

    recipe = get_owned_recipe(recipe_id, user_id)

    if recipe is None:
        return None, "not_found"

    for field in ("title", "ingredients", "instructions", "is_public"):
        if field in updates:
            setattr(recipe, field, updates[field])

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return None, "integrity_error"

    return recipe, None

def delete_recipe_for_user(
    recipe_id: int,
    user_id: int,
    role: str
):
    """Delete a recipe if the user is its owner or an admin."""

    recipe = db.session.get(Recipe, recipe_id)

    if recipe is None:
        return "not_found"

    is_owner = recipe.user_id == user_id
    is_admin = role == "admin"

    if not (is_owner or is_admin):
        return "forbidden"

    try:
        db.session.delete(recipe)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return "integrity_error"

    return None

def get_owned_recipe(recipe_id: int, user_id: int):
    """Retrieve a recipe owned by the specified user."""

    return db.session.execute(
        db.select(Recipe).where(
            Recipe.id == recipe_id,
            Recipe.user_id == user_id,
        )
    ).scalar_one_or_none()