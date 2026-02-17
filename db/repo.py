import sqlite3
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from db.conn import get_db
from core.models import Entry, DailyStats

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
