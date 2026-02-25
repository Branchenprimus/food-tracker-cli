import sqlite3
import os
import json
import hashlib
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator, Tuple
from contextlib import contextmanager
from foodtracker.models import Entry, DailyStats, GoalSettings, UserIdentity, APIKeyRecord

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
    """Create and migrate tables."""
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        is_admin INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        serving_amount REAL DEFAULT 1.0,
        kcal REAL DEFAULT 0,
        fat_g REAL DEFAULT 0,
        carbs_g REAL DEFAULT 0,
        protein_g REAL DEFAULT 0,
        confidence REAL DEFAULT 1.0,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP NULL,
        expires_at TIMESTAMP NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE INDEX IF NOT EXISTS idx_date ON entries(date);
    CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
    """
    with get_db() as conn:
        conn.executescript(schema)
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(entries)").fetchall()]
        if "user_id" not in columns:
            conn.execute("ALTER TABLE entries ADD COLUMN user_id INTEGER REFERENCES users(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_date ON entries(user_id, date)")
        legacy_owner = os.getenv("FOOD_TRACKER_LEGACY_OWNER_EMAIL")
        if not legacy_owner and os.getenv("APP_ENV", "dev") == "dev":
            legacy_owner = os.getenv("DEV_USER_EMAIL", "dev@local.foodtracker")
        if legacy_owner:
            conn.execute(
                "INSERT INTO users (email, is_admin, is_active) VALUES (?, 1, 1) ON CONFLICT(email) DO NOTHING",
                (legacy_owner.lower(),),
            )
            conn.execute(
                """
                UPDATE entries
                SET user_id = (SELECT id FROM users WHERE lower(email)=lower(?) LIMIT 1)
                WHERE user_id IS NULL
                """,
                (legacy_owner.lower(),),
            )

class EntryRepo:
    def add(self, entry: Entry) -> Entry:
        query = """
        INSERT INTO entries (user_id, title, serving_amount, kcal, fat_g, carbs_g, protein_g, confidence, date, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id, created_at
        """
        params = (
            getattr(entry, "user_id", None),
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

    def list(self, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 50, user_id: Optional[int] = None) -> List[Entry]:
        query = "SELECT * FROM entries"
        params = []
        conditions = []
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date.isoformat())
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY date DESC, time DESC LIMIT ?"
        params.append(limit)
        
        with get_db() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get(self, entry_id: int, user_id: Optional[int] = None) -> Optional[Entry]:
        query = "SELECT * FROM entries WHERE id = ?"
        params: List[Any] = [entry_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        with get_db() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def update(self, entry_id: int, updates: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Entry]:
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
            return self.get(entry_id, user_id=user_id)

        set_clause = ", ".join([f"{k} = ?" for k in db_updates.keys()])
        query = f"UPDATE entries SET {set_clause} WHERE id = ?"
        params = list(db_updates.values()) + [entry_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " RETURNING *"
        
        with get_db() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
            return None

    def delete(self, entry_id: int, user_id: Optional[int] = None) -> bool:
        query = "DELETE FROM entries WHERE id = ?"
        params: List[Any] = [entry_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        with get_db() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_daily_stats(self, day: date, user_id: Optional[int] = None) -> Optional[DailyStats]:
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
        params: List[Any] = [day.isoformat()]
        if user_id is not None:
            query = query.rstrip() + " AND user_id = ?"
            params.append(user_id)
        with get_db() as conn:
            cursor = conn.execute(query, params)
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

    def get_daily_stats_range(self, start_date: date, end_date: date, user_id: Optional[int] = None) -> List[DailyStats]:
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
        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]
        if user_id is not None:
            query = query.replace("GROUP BY date", "AND user_id = ?\n        GROUP BY date")
            params.append(user_id)
        with get_db() as conn:
            cursor = conn.execute(query, params)
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

    def get_tracked_dates(self, limit: int = 365, user_id: Optional[int] = None) -> List[date]:
        query = """
        SELECT DISTINCT date
        FROM entries
        """
        params: List[Any] = []
        if user_id is not None:
            query += " WHERE user_id = ?"
            params.append(user_id)
        query += """
        ORDER BY date DESC
        LIMIT ?
        """
        params.append(limit)
        with get_db() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> Entry:
        return Entry(
            id=row['id'],
            user_id=row['user_id'],
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
    @staticmethod
    def _goal_key(user_id: int) -> str:
        return f"goal_settings:{user_id}"

    def get_goal_settings(self, user_id: int) -> GoalSettings:
        query = "SELECT value FROM settings WHERE key = ?"
        with get_db() as conn:
            row = conn.execute(query, (self._goal_key(user_id),)).fetchone()
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

    def save_goal_settings(self, user_id: int, settings: GoalSettings) -> GoalSettings:
        query = """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """
        payload = settings.model_dump(mode="json")
        with get_db() as conn:
            conn.execute(query, (self._goal_key(user_id), json.dumps(payload)))
        return settings


class UserRepo:
    def get_by_email(self, email: str) -> Optional[UserIdentity]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, email, is_admin, is_active FROM users WHERE lower(email)=lower(?)",
                (email,),
            ).fetchone()
            if not row:
                return None
            return UserIdentity(
                id=row["id"],
                email=row["email"],
                is_admin=bool(row["is_admin"]),
                is_active=bool(row["is_active"]),
            )

    def get_by_id(self, user_id: int) -> Optional[UserIdentity]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, email, is_admin, is_active FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return UserIdentity(
                id=row["id"],
                email=row["email"],
                is_admin=bool(row["is_admin"]),
                is_active=bool(row["is_active"]),
            )

    def upsert_user(self, email: str, is_admin: bool = False, is_active: bool = True) -> UserIdentity:
        query = """
        INSERT INTO users (email, is_admin, is_active)
        VALUES (?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            is_admin=excluded.is_admin,
            is_active=excluded.is_active
        """
        with get_db() as conn:
            conn.execute(query, (email, int(is_admin), int(is_active)))
        user = self.get_by_email(email)
        if not user:
            raise RuntimeError("User upsert failed")
        return user

    def create_if_missing(self, email: str, is_admin: bool = False) -> UserIdentity:
        normalized_email = email.strip().lower()
        existing = self.get_by_email(normalized_email)
        if existing:
            return existing
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO users (email, is_admin, is_active)
                VALUES (?, ?, 1)
                ON CONFLICT(email) DO NOTHING
                """,
                (normalized_email, int(is_admin)),
            )
        user = self.get_by_email(normalized_email)
        if not user:
            raise RuntimeError("User creation failed")
        return user

    def list_users(self) -> List[UserIdentity]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, email, is_admin, is_active FROM users ORDER BY email ASC"
            ).fetchall()
        return [
            UserIdentity(
                id=row["id"],
                email=row["email"],
                is_admin=bool(row["is_admin"]),
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def update_user(self, user_id: int, is_admin: Optional[bool] = None, is_active: Optional[bool] = None) -> Optional[UserIdentity]:
        updates = []
        params: List[Any] = []
        if is_admin is not None:
            updates.append("is_admin=?")
            params.append(int(is_admin))
        if is_active is not None:
            updates.append("is_active=?")
            params.append(int(is_active))
        if not updates:
            return self.get_by_id(user_id)
        params.append(user_id)
        with get_db() as conn:
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        return self.get_by_id(user_id)


class ApiKeyRepo:
    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_key(self, user_id: int, name: str, expires_at: Optional[datetime] = None) -> Tuple[APIKeyRecord, str]:
        # Enforce exactly one key per user by removing all previous keys first.
        with get_db() as conn:
            conn.execute("DELETE FROM api_keys WHERE user_id=?", (user_id,))

        raw_key = f"ftk_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        key_prefix = raw_key[:10]
        query = """
        INSERT INTO api_keys (user_id, name, key_hash, key_prefix, expires_at)
        VALUES (?, ?, ?, ?, ?)
        RETURNING id, name, key_prefix, is_active, created_at, last_used_at, expires_at
        """
        with get_db() as conn:
            row = conn.execute(
                query,
                (user_id, name, key_hash, key_prefix, expires_at.isoformat() if expires_at else None),
            ).fetchone()
        record = APIKeyRecord(
            id=row["id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )
        return record, raw_key

    def list_user_keys(self, user_id: int) -> List[APIKeyRecord]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, name, key_prefix, is_active, created_at, last_used_at, expires_at
                FROM api_keys
                WHERE user_id=?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        out: List[APIKeyRecord] = []
        for row in rows:
            out.append(
                APIKeyRecord(
                    id=row["id"],
                    name=row["name"],
                    key_prefix=row["key_prefix"],
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                )
            )
        return out

    def revoke_key(self, user_id: int, key_id: int) -> bool:
        with get_db() as conn:
            cur = conn.execute(
                "UPDATE api_keys SET is_active=0 WHERE id=? AND user_id=?",
                (key_id, user_id),
            )
            return cur.rowcount > 0

    def authenticate(self, raw_key: str) -> Optional[Tuple[APIKeyRecord, int]]:
        key_hash = self._hash_key(raw_key)
        query = """
        SELECT id, user_id, name, key_prefix, is_active, created_at, last_used_at, expires_at
        FROM api_keys
        WHERE key_hash=?
        """
        with get_db() as conn:
            row = conn.execute(query, (key_hash,)).fetchone()
            if not row:
                return None
            if not bool(row["is_active"]):
                return None
            if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
                return None
            conn.execute("UPDATE api_keys SET last_used_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        record = APIKeyRecord(
            id=row["id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )
        return record, int(row["user_id"])
