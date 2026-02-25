from datetime import date, datetime, time, timedelta
from typing import List, Optional, Dict, Any
from foodtracker.models import Entry, DailyStats, GoalSettings
from foodtracker.db import EntryRepo, SettingsRepo, run_migrations
from foodtracker.cache import save_cache, load_cache

class FoodService:
    def __init__(self):
        self.repo = EntryRepo()
        self.settings_repo = SettingsRepo()

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
            entry_time = now.time()
        
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
        created = self.repo.add(entry)
        self.rebuild_cache()
        return created

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
        success = self.repo.delete(entry_id)
        if success:
            self.rebuild_cache()
        return success

    def update_entry(self, entry_id: int, **kwargs) -> Optional[Entry]:
        updated = self.repo.update(entry_id, kwargs)
        if updated:
            self.rebuild_cache()
        return updated

    def get_current_streak(self) -> int:
        tracked_dates = self.repo.get_tracked_dates()
        if not tracked_dates:
            return 0
        
        today = date.today()
        tracked_dates.sort(reverse=True)
        
        last_entry = tracked_dates[0]
        diff = (today - last_entry).days
        
        if diff > 1:
            return 0
            
        streak = 0
        current_check = last_entry
        
        for d in tracked_dates:
            if d == current_check:
                streak += 1
                current_check = d - timedelta(days=1)
            else:
                break
                
        return streak

    def get_stats_history(self, start_date: date, end_date: date) -> List[DailyStats]:
        return self.repo.get_daily_stats_range(start_date, end_date)

    def get_goal_settings(self) -> GoalSettings:
        return self.settings_repo.get_goal_settings()

    def save_goal_settings(self, settings: GoalSettings) -> GoalSettings:
        return self.settings_repo.save_goal_settings(settings)

    def rebuild_cache(self):
        """Rebuild the widget cache JSON."""
        today = date.today()
        
        # Calculate today's stats
        day_stats = self.get_daily_summary(today)
        
        # Calculate week stats
        # For simplicity, let's say "week" means "last 7 days" including today
        week_start = today - timedelta(days=6)
        week_history = self.get_stats_history(week_start, today)
        
        # Aggregate week stats
        week_total_kcal = sum(d.total_kcal for d in week_history)
        week_total_protein = sum(d.total_protein for d in week_history)
        week_total_carbs = sum(d.total_carbs for d in week_history)
        week_total_fat = sum(d.total_fat for d in week_history)
        
        week_stats = {
            "total_kcal": week_total_kcal,
            "total_protein": week_total_protein,
            "total_carbs": week_total_carbs,
            "total_fat": week_total_fat,
            "days_tracked": len(week_history)
        }
        
        # Get streak
        streak = self.get_current_streak()

        data = {
            "generated_at": datetime.now().isoformat(),
            "timezone": "Europe/Berlin", # Hardcoded as per requirement/example
            "day": day_stats.model_dump(mode='json'),
            "week": week_stats,
            "streak": streak
        }
        
        save_cache(data)
