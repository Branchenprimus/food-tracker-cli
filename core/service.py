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

    def get_current_streak(self) -> int:
        # Get distinct dates with entries
        tracked_dates = self.repo.get_tracked_dates()
        if not tracked_dates:
            return 0
        
        today = date.today()
        # sort desc just in case, though repo does it
        tracked_dates.sort(reverse=True)
        
        # Check if the streak is alive (entry today or yesterday)
        last_entry = tracked_dates[0]
        diff = (today - last_entry).days
        
        if diff > 1:
            return 0
            
        # Calculate streak
        streak = 0
        # Start checking from the most recent entry
        current_check = last_entry
        
        for d in tracked_dates:
            if d == current_check:
                streak += 1
                current_check = current_check.replace(day=current_check.day - 1) if current_check.day > 1 else (current_check.replace(month=current_check.month - 1, day=28) if current_check.month > 1 else current_check.replace(year=current_check.year - 1, month=12, day=31))
                # The above date subtraction logic is buggy/complex without timedelta. 
                # Better to use timedelta.
                from datetime import timedelta
                current_check = d - timedelta(days=1)
            else:
                break
                
        return streak

    def get_stats_history(self, start_date: date, end_date: date) -> List[DailyStats]:
        """Get daily stats for a specific date range."""
        return self.repo.get_daily_stats_range(start_date, end_date)
