
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt  # PyJWT
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
# --- Config -----------------------------------------------------------------

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 1
DATABASE = "recipes.db"
MIN_PASSWORD_LENGTH = 8
MAX_PAGE_SIZE = 100

app = Flask(__name__)


# --- Database ---------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if missing, and add recipes.user_id to older databases."""
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title        TEXT NOT NULL,
            ingredients  TEXT NOT NULL,
            instructions TEXT NOT NULL DEFAULT '',
            is_public    INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    # Older databases: add the owner column. Existing rows get NULL (unowned),
    # so only public ones stay visible and nobody can edit them.
    columns = [r[1] for r in db.execute("PRAGMA table_info(recipes)")]
    if "user_id" not in columns:
        db.execute("ALTER TABLE recipes ADD COLUMN user_id INTEGER REFERENCES users(id)")
    db.commit()
    db.close()


# --- Helpers ----------------------------------------------------------------

def recipe_to_dict(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


def is_nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def make_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "iat": now,
        "role": user["role"],
        "exp": now + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def user_id_from_request():
    """Return (user_id, error_message). user_id is None if no valid token."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, "missing token"
    try:
        payload = jwt.decode(header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"]), None
    except jwt.ExpiredSignatureError:
        return None, "token expired"
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None, "invalid token"


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        identity, error = identity_from_request()
        if identity is None:
            return jsonify({"error": error}), 401

        g.user_id = identity["user_id"]
        g.username = identity["username"]
        g.role = identity["role"]
        return f(*args, **kwargs)

    return wrapper

def identity_from_request():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, "missing or invalid Authorization header"

    token = auth_header.split(" ", 1)[1]

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "user_id": int(decoded["sub"]),
            "username": decoded["username"],
            "role": decoded["role"],
        }, None
    except jwt.ExpiredSignatureError:
        return None, "token expired"
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None, "invalid token"

def optional_auth(f):
    """Sets g.user_id if a valid token is sent, otherwise None."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        g.user_id, _ = user_id_from_request()
        return f(*args, **kwargs)

    return wrapper


def get_visible_recipe(recipe_id):
    """A recipe is visible if it is public or owned by the current user."""
    return get_db().execute(
        "SELECT * FROM recipes WHERE id = ? AND (is_public = 1 OR user_id = ?)",
        (recipe_id, g.user_id),
    ).fetchone()


def get_owned_recipe(recipe_id):
    return get_db().execute(
        "SELECT * FROM recipes WHERE id = ? AND user_id = ?",
        (recipe_id, g.user_id),
    ).fetchone()


# --- Routes: general --------------------------------------------------------

@app.get("/")
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


# --- Routes: auth -----------------------------------------------------------

@app.post("/register")
def register():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("username"))
        or not is_nonempty_str(data.get("email"))
        or not isinstance(data.get("password"), str)
    ):
        return jsonify({"error": "username, email, and password are required"}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]

    if "@" not in email:
        return jsonify({"error": "a valid email is required"}), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify(
            {"error": f"password must be at least {MIN_PASSWORD_LENGTH} characters"}
        ), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "user already exists"}), 409

    return jsonify({"id": cur.lastrowid, "username": username, "email": email}), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("username"))
        or not isinstance(data.get("password"), str)
    ):
        return jsonify({"error": "username and password are required"}), 400

    username = data["username"].strip()
    password = data["password"]

    user = get_db().execute(
    "SELECT id, username, password_hash, role FROM users WHERE username = ?",
    (username,),
).fetchone()

    # Same response for unknown user and wrong password.
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify(
        {
            "token": make_token(user),
            "user": {"id": user["id"], "username": user["username"]},
        }
    ), 200


# --- Routes: recipes --------------------------------------------------------

@app.get("/recipes")
@require_auth
def list_recipes():
    try:
        limit = min(int(request.args.get("limit", 20)), MAX_PAGE_SIZE)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400
    if limit < 1 or offset < 0:
        return jsonify({"error": "limit must be >= 1 and offset >= 0"}), 400

    rows = get_db().execute(
        "SELECT * FROM recipes WHERE is_public = 1 OR user_id = ? "
        "ORDER BY id LIMIT ? OFFSET ?",
        (g.user_id, limit, offset),
    ).fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.get("/recipes/<int:recipe_id>")
@optional_auth
def get_recipe(recipe_id):
    row = get_visible_recipe(recipe_id)
    if row is None:
        return jsonify({"error": "recipe not found"}), 404
    return jsonify(recipe_to_dict(row))


@app.post("/recipes")
@require_auth
def create_recipe():
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("title"))
        or not is_nonempty_str(data.get("ingredients"))
    ):
        return jsonify({"error": "title and ingredients are required strings"}), 400

    instructions = data.get("instructions", "")
    if not isinstance(instructions, str):
        return jsonify({"error": "instructions must be a string"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes (user_id, title, ingredients, instructions, is_public)"
            " VALUES (?, ?, ?, ?, ?)",
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
        return jsonify({"error": "could not create recipe (duplicate title?)"}), 409

    row = db.execute("SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(recipe_to_dict(row)), 201


@app.patch("/recipes/<int:recipe_id>")
@require_auth
def update_recipe(recipe_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "a JSON body is required"}), 400

    # Hide other users' recipes: 404 whether missing or not yours.
    if get_owned_recipe(recipe_id) is None:
        return jsonify({"error": "recipe not found"}), 404

    fields, values = [], []
    for column in ("title", "ingredients"):
        if column in data:
            if not is_nonempty_str(data[column]):
                return jsonify({"error": f"{column} must be a non-empty string"}), 400
            fields.append(f"{column} = ?")
            values.append(data[column].strip() if column == "title" else data[column])
    if "instructions" in data:
        if not isinstance(data["instructions"], str):
            return jsonify({"error": "instructions must be a string"}), 400
        fields.append("instructions = ?")
        values.append(data["instructions"])
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)

    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.extend([recipe_id, g.user_id])
    db = get_db()
    try:
        db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            values,
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "could not update recipe (duplicate title?)"}), 409

    return jsonify(recipe_to_dict(get_owned_recipe(recipe_id)))


@app.delete("/recipes/<int:recipe_id>")
@require_auth
def delete_recipe(recipe_id):
    db = get_db()

    # 1. Load the recipe by ID only
    recipe = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,)
    ).fetchone()

    # 2. Recipe doesn't exist → 404
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    # 3. Permission check:
    #    - admins can delete any recipe
    #    - ordinary users can delete only their own recipes
    is_owner = (recipe["user_id"] == g.user_id)
    is_admin = (getattr(g, "role", None) == "admin")

    if not (is_owner or is_admin):
        return jsonify({"error": "forbidden: you cannot delete this recipe"}), 403

    # 4. Authorized → DELETE
    db.execute(
        "DELETE FROM recipes WHERE id = ?",
        (recipe_id,)
    )
    db.commit()

    return "", 204


# curl -i -X POST http://127.0.0.1:5000/login   -H "Content-Type: application/json"   -d '{
# "username": "rachel.test1",
# "email": "rachel.test1@example.com",
# "password": "SuperSecret123"
# }'

# --- Entry point ------------------------------------------------------------

init_db()

if __name__ == "__main__":
    # debug=True is for local development only.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")