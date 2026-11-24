
import sqlite3
from uuid import uuid4

from app import create_test_app
from app.config import DevelopmentConfig


# Create the testing application
app = create_test_app()

# Create the Flask test client
client = app.test_client()


# --- Database Helper -----------------------------------

def count_users(database):
    with sqlite3.connect(database) as db:
        return db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]


# --- Database Counts Before Testing --------------------

dev_db = DevelopmentConfig.DATABASE
test_db = app.config["DATABASE"]

dev_before = count_users(dev_db)
test_before = count_users(test_db)

print("\n--- BEFORE TEST ---")
print("Development users:", dev_before)
print("Testing users:", test_before)


# --- Register User -------------------------------------

# Generate a unique username for each test run
unique_id = uuid4().hex[:8]

username = f"test_user_{unique_id}"
email = f"{username}@example.com"
password = "TestPassword123!"

register_response = client.post(
    "/register",
    json={
        "username": username,
        "email": email,
        "password": password,
    },
)

print("\n--- REGISTER ---")
print("Status:", register_response.status_code)
print("JSON:", register_response.get_json())

assert register_response.status_code == 201


# --- Login User ----------------------------------------

login_response = client.post(
    "/login",
    json={
        "username": username,
        "password": password,
    },
)

print("\n--- LOGIN ---")
print("Response Status:", login_response.status_code)
print("JSON:", login_response.get_json())

assert login_response.status_code == 200

token = login_response.get_json()["token"]

assert token


# --- Database Counts After Testing ---------------------

dev_after = count_users(dev_db)
test_after = count_users(test_db)

print("\n--- AFTER TEST ---")
print("Development users:", dev_after)
print("Testing users:", test_after)


# --- Verify Database Isolation -------------------------

assert dev_after == dev_before, "Development database changed!"
assert test_after == test_before + 1, "Test user was not created!"

print("\nAll tests passed!")
print("Development database is unchanged.")
