import os
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, HTTPException, Header
from typing import Optional, List, Dict, Any
from datetime import date
from foodtracker.service import FoodService
from foodtracker.models import Entry, DailyStats
from foodtracker.cache import load_cache

app = FastAPI()
service = FoodService()

CMD_VERSION = os.getenv("APP_VERSION", "dev")
CMD_ENV = os.getenv("APP_ENV", "dev")
CMD_COMMIT = os.getenv("APP_COMMIT", "unknown")
CMD_REPOSITORY = os.getenv("APP_REPOSITORY", "Branchenprimus/food-tracker-cli")

@app.get("/api/info")
def get_info():
    has_commit = bool(CMD_COMMIT and CMD_COMMIT != "unknown")
    short_commit = CMD_COMMIT[:7] if has_commit else CMD_COMMIT
    commit_url = f"https://github.com/{CMD_REPOSITORY}/commit/{CMD_COMMIT}" if has_commit else ""
    return {
        "version": CMD_VERSION,
        "env": CMD_ENV,
        "commit": CMD_COMMIT,
        "display_version": f"{CMD_VERSION}@{short_commit}" if short_commit else CMD_VERSION,
        "commit_url": commit_url
    }

# Serve static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("web/static/index.html")

# Existing API endpoints (using Service -> DB)
@app.get("/api/entries", response_model=List[Entry])
def get_entries(date: Optional[date] = None):
    if date:
        return service.list_entries(from_date=date, to_date=date, limit=1000)
    return service.list_entries(limit=100)

@app.post("/api/entries", response_model=Entry)
def add_entry(entry: Entry):
    return service.add_entry(
        title=entry.title,
        kcal=entry.kcal,
        fat=entry.fat_g,
        carbs=entry.carbs_g,
        protein=entry.protein_g,
        serving=entry.serving_amount,
        confidence=entry.confidence,
        entry_date=entry.entry_date,
        entry_time=entry.entry_time
    )

@app.put("/api/entries/{entry_id}", response_model=Entry)
def update_entry(entry_id: int, entry: Entry):
    updated = service.update_entry(
        entry_id,
        title=entry.title,
        kcal=entry.kcal,
        fat_g=entry.fat_g,
        carbs_g=entry.carbs_g,
        protein_g=entry.protein_g,
        serving_amount=entry.serving_amount,
        confidence=entry.confidence,
        entry_date=entry.entry_date,
        entry_time=entry.entry_time
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Entry not found")
    return updated

@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: int):
    success = service.delete_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "success"}

@app.get("/api/stats/day", response_model=DailyStats)
def get_daily_stats(date: Optional[date] = None):
    return service.get_daily_summary(date)

@app.get("/api/stats/streak")
def get_streak():
    streak = service.get_current_streak()
    return {"streak": streak}

@app.get("/api/stats/history", response_model=List[DailyStats])
def get_history(start: date, end: date):
    return service.get_stats_history(start, end)

# In-memory cache with mtime tracking
_cache_data: Optional[Dict[str, Any]] = None
_cache_mtime: Optional[float] = None
AUTH_TOKEN = os.getenv("WIDGET_API_TOKEN")

def _load_cache_if_changed() -> Dict[str, Any]:
    global _cache_data, _cache_mtime

    # Construct Path object check
    # We use the path defined in foodtracker.cache but we can re-import or use env
    from foodtracker.cache import CACHE_PATH
    
    try:
        stat = CACHE_PATH.stat()
    except FileNotFoundError:
        # If cache missing, try to rebuild once
        try:
            service.rebuild_cache()
            stat = CACHE_PATH.stat()
        except Exception:
             raise HTTPException(status_code=503, detail="Widget cache missing")

    mtime = stat.st_mtime

    # Fast path: unchanged
    if _cache_data is not None and _cache_mtime == mtime:
        return _cache_data

    # Reload
    try:
        raw = CACHE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Widget cache unreadable: {type(e).__name__}")

    _cache_data = data
    _cache_mtime = mtime
    return data

def _auth(authorization: Optional[str]) -> None:
    if not AUTH_TOKEN:
        return  # auth disabled
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.get("/v1/widget/today")
def widget_today(authorization: Optional[str] = Header(default=None)):
    """
    Get cached widget data.
    This endpoint does NO DB calls.
    It reads from the JSON cache file or memory.
    """
    _auth(authorization)
    data = _load_cache_if_changed()
    # Response is already JSON serializable; return as-is
    return JSONResponse(content=data)
