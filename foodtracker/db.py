import sqlite3
import os
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from contextlib import contextmanager
from foodtracker.models import Entry, DailyStats, GoalSettings

# Default DB Path - can be overridden by env var
DB_PATH = Path(os.getenv("FOOD_TRACKER_DB", "data/app.db"))

def ensure_dirs():
    """Ensure the database directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_db_path() -> Path:
    ensure_dirs()
    return DB_PATH

def create_connection() -> sqlite3.Connection:
    """Create a database connection with optimal settings."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    
    # Durability and integrity pragmas.
    # FULL gives stronger guarantees against power-loss at the cost of some write speed.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    
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

def run_migrations():
    """Create tables if they don't exist."""
    schema = """
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        serving_amount REAL DEFAULT 1.0,
        kcal REAL DEFAULT 0,
        fat_g REAL DEFAULT 0,
        carbs_g REAL DEFAULT 0,
        protein_g REAL DEFAULT 0,
        confidence REAL DEFAULT 1.0,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_date ON entries(date);
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """
    with get_db() as conn:
        conn.executescript(schema)

class EntryRepo:
    def add(self, entry: Entry) -> Entry:
        query = """
        INSERT INTO entries (title, serving_amount, kcal, fat_g, carbs_g, protein_g, confidence, date, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id, created_at
        """
        params = (
            entry.title, entry.serving_amount, entry.kcal, entry.fat_g, 
            entry.carbs_g, entry.protein_g, entry.confidence, 
            entry.entry_date.isoformat(), entry.entry_time.strftime("%H:%M")
        )
        
        with get_db() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            entry.id = row['id']
            # created_at is not currently on the model but returned by DB
            return entry

    def list(self, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 50) -> List[Entry]:
        query = "SELECT * FROM entries"
        params = []
        conditions = []
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date.isoformat())
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY date DESC, time DESC LIMIT ?"
        params.append(limit)
        
        with get_db() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get(self, entry_id: int) -> Optional[Entry]:
        query = "SELECT * FROM entries WHERE id = ?"
        with get_db() as conn:
            cursor = conn.execute(query, (entry_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def update(self, entry_id: int, updates: Dict[str, Any]) -> Optional[Entry]:
        # updates is a dict of field names to values
        # We need to map model field names to DB columns if they differ
        # (currently they match mostly, but entry_date -> date, entry_time -> time)
        
        db_updates = {}
        for key, value in updates.items():
            if key == 'entry_date':
                db_updates['date'] = value.isoformat() if value else None
            elif key == 'entry_time':
                db_updates['time'] = value.strftime("%H:%M") if value else None
            elif key in ['title', 'serving_amount', 'kcal', 'fat_g', 'carbs_g', 'protein_g', 'confidence']:
                db_updates[key] = value
        
        if not db_updates:
            return self.get(entry_id)

        set_clause = ", ".join([f"{k} = ?" for k in db_updates.keys()])
        query = f"UPDATE entries SET {set_clause} WHERE id = ? RETURNING *"
        params = list(db_updates.values()) + [entry_id]
        
        with get_db() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def delete(self, entry_id: int) -> bool:
        query = "DELETE FROM entries WHERE id = ?"
        with get_db() as conn:
            cursor = conn.execute(query, (entry_id,))
            return cursor.rowcount > 0

    def get_daily_stats(self, day: date) -> Optional[DailyStats]:
        query = """
        SELECT 
            COUNT(*) as entry_count,
            SUM(kcal) as total_kcal,
            SUM(protein_g) as total_protein,
            SUM(carbs_g) as total_carbs,
            SUM(fat_g) as total_fat
        FROM entries 
        WHERE date = ?
        """
        with get_db() as conn:
            cursor = conn.execute(query, (day.isoformat(),))
            row = cursor.fetchone()
            if row and row['entry_count'] > 0:
                return DailyStats(
                    date=day,
                    total_kcal=row['total_kcal'] or 0,
                    total_protein=row['total_protein'] or 0,
                    total_carbs=row['total_carbs'] or 0,
                    total_fat=row['total_fat'] or 0,
                    entry_count=row['entry_count']
                )
            return None

    def get_daily_stats_range(self, start_date: date, end_date: date) -> List[DailyStats]:
        query = """
        SELECT 
            date,
            COUNT(*) as entry_count,
            SUM(kcal) as total_kcal,
            SUM(protein_g) as total_protein,
            SUM(carbs_g) as total_carbs,
            SUM(fat_g) as total_fat
        FROM entries 
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
        """
        with get_db() as conn:
            cursor = conn.execute(query, (start_date.isoformat(), end_date.isoformat()))
            results = []
            for row in cursor.fetchall():
                results.append(DailyStats(
                    date=datetime.strptime(row['date'], "%Y-%m-%d").date(),
                    total_kcal=row['total_kcal'] or 0,
                    total_protein=row['total_protein'] or 0,
                    total_carbs=row['total_carbs'] or 0,
                    total_fat=row['total_fat'] or 0,
                    entry_count=row['entry_count']
                ))
            return results

    def get_tracked_dates(self, limit: int = 365) -> List[date]:
        query = """
        SELECT DISTINCT date
        FROM entries
        ORDER BY date DESC
        LIMIT ?
        """
        with get_db() as conn:
            cursor = conn.execute(query, (limit,))
            rows = cursor.fetchall()
            return [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> Entry:
        return Entry(
            id=row['id'],
            title=row['title'],
            serving_amount=row['serving_amount'],
            kcal=row['kcal'],
            fat_g=row['fat_g'],
            carbs_g=row['carbs_g'],
            protein_g=row['protein_g'],
            confidence=row['confidence'],
            entry_date=datetime.strptime(row['date'], "%Y-%m-%d").date(),
            entry_time=datetime.strptime(row['time'], "%H:%M").time()
        )


class SettingsRepo:
    GOAL_SETTINGS_KEY = "goal_settings"

    def get_goal_settings(self) -> GoalSettings:
        query = "SELECT value FROM settings WHERE key = ?"
        with get_db() as conn:
            row = conn.execute(query, (self.GOAL_SETTINGS_KEY,)).fetchone()
            if not row:
                return GoalSettings()
            try:
                raw = json.loads(row["value"])
            except (TypeError, json.JSONDecodeError):
                return GoalSettings()
            return GoalSettings(
                body_weight_kg=float(raw.get("body_weight_kg", 80.0)),
                weight_loss_per_week_kg=float(raw.get("weight_loss_per_week_kg", 0.3)),
            )

    def save_goal_settings(self, settings: GoalSettings) -> GoalSettings:
        query = """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """
        payload = settings.model_dump(mode="json")
        with get_db() as conn:
            conn.execute(query, (self.GOAL_SETTINGS_KEY, json.dumps(payload)))
        return settings
