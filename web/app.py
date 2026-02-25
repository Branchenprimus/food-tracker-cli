from fastapi import FastAPI, HTTPException, Body
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from core.service import FoodService
from core.models import Entry, DailyStats

app = FastAPI()
service = FoodService()

CMD_VERSION = os.getenv("APP_VERSION", "dev")
CMD_ENV = os.getenv("APP_ENV", "dev")
CMD_COMMIT = os.getenv("APP_COMMIT", "unknown")
CMD_REPOSITORY = os.getenv("APP_REPOSITORY", "Branchenprimus/food-tracker-cli")
CMD_GIT_REF = os.getenv("APP_GIT_REF", "dev" if CMD_ENV == "dev" else "master")

@app.get("/api/info")
def get_info():
    has_commit = bool(CMD_COMMIT and CMD_COMMIT != "unknown")
    short_commit = CMD_COMMIT[:7] if has_commit else CMD_COMMIT
    ref_url = f"https://github.com/{CMD_REPOSITORY}/tree/{CMD_GIT_REF}"
    commit_url = f"https://github.com/{CMD_REPOSITORY}/commit/{CMD_COMMIT}?branch={CMD_GIT_REF}" if has_commit else ref_url
    return {
        "version": CMD_VERSION,
        "env": CMD_ENV,
        "commit": CMD_COMMIT,
        "git_ref": CMD_GIT_REF,
        "display_version": f"{CMD_VERSION}@{short_commit}" if short_commit else CMD_VERSION,
        "commit_url": commit_url,
        "ref_url": ref_url
    }

# Serve static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("web/static/index.html")

@app.get("/api/entries", response_model=List[Entry])
def get_entries(date: Optional[date] = None):
    # If date is provided, filter by that day (start and end = date)
    if date:
        return service.list_entries(from_date=date, to_date=date, limit=1000)
    return service.list_entries(limit=100)

@app.post("/api/entries", response_model=Entry)
def add_entry(entry: Entry):
    # We use the service to add, which handles ID generation
    # But Entry model requires ID? No, ID is optional.
    created = service.add_entry(
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
    return created

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
