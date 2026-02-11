from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from core.models import Entry, DailyStats
from db.repo import EntryRepo
from db.migrations import run_migrations

class FoodService:
    def __init__(self):
        self.repo = EntryRepo()

    def init_db(self):
        """Initialize the database and run migrations."""
        run_migrations()

    def add_entry(self, title: str, kcal: float, fat: float, carbs: float, protein: float, 
                 serving: float = 1.0, confidence: float = 0.7, 
                 entry_date: Optional[date] = None, entry_time: Optional[time] = None) -> Entry:
        
        now = datetime.now()
        if not entry_date:
            entry_date = now.date()
        if not entry_time:
            entry_time = now.time() # This will include seconds/microseconds, model serializes to HH:MM

        # Clean time to HH:MM for consistency with DB check constraint if strict, 
        # but the model validator might handle it. 
        # The DB check is length(time)=5, so we MUST format it as HH:MM string in the repo.
        # The model just holds a time object.
        # Let's ensure seconds are stripped if we want clean simple times
        entry_time = entry_time.replace(second=0, microsecond=0)

        entry = Entry(
            title=title,
            serving_amount=serving,
            kcal=kcal,
            fat_g=fat,
            carbs_g=carbs,
            protein_g=protein,
            confidence=confidence,
            entry_date=entry_date,
            entry_time=entry_time
        )
        return self.repo.add(entry)

    def list_entries(self, from_date: Optional[date] = None, to_date: Optional[date] = None, limit: int = 50) -> List[Entry]:
        return self.repo.list(start_date=from_date, end_date=to_date, limit=limit)

    def get_daily_summary(self, day: Optional[date] = None) -> DailyStats:
        if not day:
            day = date.today()
        stats = self.repo.get_daily_stats(day)
        if not stats:
            return DailyStats(date=day, total_kcal=0, total_protein=0, total_carbs=0, total_fat=0, entry_count=0)
        return stats
    
    def delete_entry(self, entry_id: int) -> bool:
        return self.repo.delete(entry_id)

    def update_entry(self, entry_id: int, **kwargs) -> Optional[Entry]:
        return self.repo.update(entry_id, kwargs)
