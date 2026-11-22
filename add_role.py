import sqlite3

connection = sqlite3.connect("recipes.db")

try:
    connection.execute("""
        ALTER TABLE users
        ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'admin'))
    """)

    connection.commit()
    print("Successfully added roles!")

finally:
    connection.close()