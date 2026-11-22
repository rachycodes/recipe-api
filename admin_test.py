import sqlite3

connection = sqlite3.connect("recipes.db")

try:
    cursor = connection.execute(
        "UPDATE users SET role = ? WHERE username = ?",
        ("admin", "rachel.test1")
    )

    connection.commit()

    if cursor.rowcount > 0:
        print("rachel.test1 is now an admin!")
    else:
        print("User not found.")

finally:
    connection.close()