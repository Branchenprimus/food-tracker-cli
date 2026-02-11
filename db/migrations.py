import sqlite3
import os
from pathlib import Path
from db.conn import get_db

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def init_migrations_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        );
    """)

def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}

def run_migrations():
    """Apply all pending migrations."""
    if not MIGRATIONS_DIR.exists():
        os.makedirs(MIGRATIONS_DIR)
        return

    with get_db() as conn:
        init_migrations_table(conn)
        applied = get_applied_migrations(conn)
        
        # Get all .sql files, sorted by name
        migration_files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")])
        
        for filename in migration_files:
            if filename not in applied:
                print(f"Applying migration: {filename}")
                filepath = MIGRATIONS_DIR / filename
                with open(filepath, "r") as f:
                    script = f.read()
                
                try:
                    conn.executescript(script)
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (filename,))
                    print(f"Applied {filename}")
                except Exception as e:
                    print(f"Error applying {filename}: {e}")
                    raise
