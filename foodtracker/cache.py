import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import date, datetime

# Cache file path
CACHE_PATH = Path(os.getenv("FOOD_TRACKER_CACHE", "data/widget_cache.json"))

def ensure_cache_dir():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def save_cache(data: Dict[str, Any]):
    """
    Atomically write data to cache file.
    Writes to a temp file first, then moves it to the destination.
    This ensures that readers never see a partial write.
    """
    ensure_cache_dir()
    
    # Create temp file in the same directory
    tmp_path = CACHE_PATH.with_suffix(CACHE_PATH.suffix + ".tmp")
    
    # Ensure deterministic JSON (no pretty print; faster to read/parse)
    # separators=(",", ":") removes whitespace
    raw = json.dumps(data, default=json_serial, ensure_ascii=False, separators=(",", ":"))
    
    try:
        tmp_path.write_text(raw, encoding="utf-8")
        # Atomic rename
        os.replace(tmp_path, CACHE_PATH)
    except OSError:
        if tmp_path.exists():
            os.remove(tmp_path)
        raise

def load_cache() -> Optional[Dict[str, Any]]:
    """Load data from cache file."""
    if not CACHE_PATH.exists():
        return None
        
    try:
        with open(CACHE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
