import os
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import Blueprint, g, jsonify, request
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from ..db import get_db
from ..utils import is_nonempty_str

load_dotenv()


# --- Configuration -------------------------------------------------

JWT_SECRET = os.environ.get("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 1
MIN_PASSWORD_LENGTH = 8


# --- Blueprint -----------------------------------------------------

auth_bp = Blueprint("auth", __name__)


# --- JWT Helpers ---------------------------------------------------

def make_token(user):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "iat": now,
        "role": user["role"],
        "exp": now + timedelta(hours=JWT_EXPIRES_HOURS),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def user_id_from_request():
    """Return the user ID if a valid token is provided."""

    header = request.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return None, "missing token"

    try:
        payload = jwt.decode(
            header[7:],
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        return int(payload["sub"]), None

    except jwt.ExpiredSignatureError:
        return None, "token expired"

    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        return None, "invalid token"


def identity_from_request():
    """Extract the user's identity and role from a JWT."""

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None, "missing or invalid Authorization header"

    token = auth_header.split(" ", 1)[1]

    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        return {
            "user_id": int(decoded["sub"]),
            "username": decoded["username"],
            "role": decoded["role"],
        }, None

    except jwt.ExpiredSignatureError:
        return None, "token expired"

    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        return None, "invalid token"


# --- Authentication Middleware -------------------------------------

def require_auth(f):
    """Require a valid JWT before accessing a protected route."""

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


def optional_auth(f):
    """Set g.user_id if a valid token is provided."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        g.user_id, _ = user_id_from_request()

        return f(*args, **kwargs)

    return wrapper


# --- Registration Route --------------------------------------------

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("username"))
        or not is_nonempty_str(data.get("email"))
        or not isinstance(data.get("password"), str)
    ):
        return jsonify({
            "error": "username, email, and password are required"
        }), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]

    if "@" not in email:
        return jsonify({
            "error": "a valid email is required"
        }), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "error": f"password must be at least {MIN_PASSWORD_LENGTH} characters"
        }), 400

    db = get_db()

    try:
        cur = db.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (
                username,
                email,
                generate_password_hash(password),
            ),
        )

        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()

        return jsonify({
            "error": "user already exists"
        }), 409

    return jsonify({
        "id": cur.lastrowid,
        "username": username,
        "email": email,
    }), 201


# --- Login Route ---------------------------------------------------

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not is_nonempty_str(data.get("username"))
        or not isinstance(data.get("password"), str)
    ):
        return jsonify({
            "error": "username and password are required"
        }), 400

    username = data["username"].strip()
    password = data["password"]

    user = get_db().execute(
        """
        SELECT id, username, password_hash, role
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(
        user["password_hash"],
        password,
    ):
        return jsonify({
            "error": "Invalid credentials"
        }), 401

    return jsonify({
        "token": make_token(user),
        "user": {
            "id": user["id"],
            "username": user["username"],
        },
    }), 200
