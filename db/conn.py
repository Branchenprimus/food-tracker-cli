import sqlite3
from pathlib import Path
from typing import Generator
from contextlib import contextmanager
from config.config import DB_PATH, ensure_dirs

def get_db_path() -> Path:
    ensure_dirs()
    return DB_PATH

def create_connection() -> sqlite3.Connection:
    """Create a database connection with optimal settings."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    
    # Performance and integrity pragmas
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    # Return rows as dictionaries (optional, but useful)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = create_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
