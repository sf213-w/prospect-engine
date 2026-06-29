"""
Quick diagnostic: list which tables exist in pipeline.db, and confirm
the database path being used. Run with:

    python check_db.py
"""

from storage.db import DB_PATH, get_connection

print(f"Database path: {DB_PATH}")
print(f"File exists: {DB_PATH.exists()}")

conn = get_connection()
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
tables = [r[0] for r in rows]
print(f"Tables found: {tables}")

if "tags" not in tables:
    print("\n-> 'tags' table is MISSING. Run: python -c \"from storage.db import init_db; init_db()\"")
else:
    print("\n-> 'tags' table exists. You're good to run categorize_articles.py")

conn.close()