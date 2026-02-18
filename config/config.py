import os
from pathlib import Path

# Default paths
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "food" / "food.db"
if os.name == 'nt': # Windows fallback just in case
    DEFAULT_DB_PATH = Path.home() / "AppData" / "Local" / "food" / "food.db"

# Environment overrides
DB_PATH = Path(os.getenv("FOOD_DB_PATH", DEFAULT_DB_PATH)).expanduser()

# Defaults
DEFAULT_CONFIDENCE = 0.7
DEFAULT_CHART_DAYS = 7

# Date/Time Formats
DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"

def ensure_dirs():
    """Ensure the database directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
