import os
import json
import re
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from foodtracker.service import FoodService
from foodtracker.models import (
    Entry,
    DailyStats,
    GoalSettings,
    UserIdentity,
    APIKeyRecord,
    APIKeyCreateRequest,
    APIKeyCreateResponse,
)
from foodtracker.cache import load_cache

app = FastAPI()
service = FoodService()

CMD_VERSION = os.getenv("APP_VERSION", "dev")
CMD_ENV = os.getenv("APP_ENV", "dev")
CMD_COMMIT = os.getenv("APP_COMMIT", "unknown")
CMD_REPOSITORY = os.getenv("APP_REPOSITORY", "Branchenprimus/food-tracker-cli")
CMD_GIT_REF = os.getenv("APP_GIT_REF", "dev" if CMD_ENV == "dev" else "master")
DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", "dev@local.foodtracker")
ALLOW_LOCAL_FALLBACK_IDENTITY = os.getenv("ALLOW_LOCAL_FALLBACK_IDENTITY", "0") == "1"


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _extract_api_key(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return None


def get_current_user(cf_email: Optional[str] = Header(default=None, alias="CF-Access-Authenticated-User-Email")) -> UserIdentity:
    if cf_email:
        email = cf_email.strip().lower()
    elif CMD_ENV == "dev":
        email = DEV_USER_EMAIL.lower()
    elif ALLOW_LOCAL_FALLBACK_IDENTITY:
        # Optional escape hatch for local deploy-mode testing without Cloudflare Access.
        email = DEV_USER_EMAIL.lower()
    else:
        raise HTTPException(status_code=401, detail="Missing Cloudflare user identity header")

    if not _is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid user email in Cloudflare header")

    user = service.ensure_user(email=email)
    return user

@app.get("/api/info")
def get_info():
    has_commit = bool(CMD_COMMIT and CMD_COMMIT != "unknown")
    short_commit = CMD_COMMIT[:7] if has_commit else CMD_COMMIT
    ref_url = f"https://github.com/{CMD_REPOSITORY}/tree/{CMD_GIT_REF}"
    commit_url = f"https://github.com/{CMD_REPOSITORY}/tree/{CMD_COMMIT}" if has_commit else ref_url
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

# Existing API endpoints (using Service -> DB)
@app.get("/api/entries", response_model=List[Entry])
def get_entries(date: Optional[date] = None, user: UserIdentity = Depends(get_current_user)):
    if date:
        return service.list_entries(from_date=date, to_date=date, limit=1000, user_id=user.id)
    return service.list_entries(limit=100, user_id=user.id)

@app.post("/api/entries", response_model=Entry)
def add_entry(entry: Entry, user: UserIdentity = Depends(get_current_user)):
    return service.add_entry(
        title=entry.title,
        kcal=entry.kcal,
        fat=entry.fat_g,
        carbs=entry.carbs_g,
        protein=entry.protein_g,
        serving=entry.serving_amount,
        confidence=entry.confidence,
        entry_date=entry.entry_date,
        entry_time=entry.entry_time,
        user_id=user.id
    )

@app.put("/api/entries/{entry_id}", response_model=Entry)
def update_entry(entry_id: int, entry: Entry, user: UserIdentity = Depends(get_current_user)):
    updated = service.update_entry(
        entry_id,
        user_id=user.id,
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
def delete_entry(entry_id: int, user: UserIdentity = Depends(get_current_user)):
    success = service.delete_entry(entry_id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "success"}

@app.get("/api/stats/day", response_model=DailyStats)
def get_daily_stats(date: Optional[date] = None, user: UserIdentity = Depends(get_current_user)):
    return service.get_daily_summary(date, user_id=user.id)

@app.get("/api/stats/streak")
def get_streak(user: UserIdentity = Depends(get_current_user)):
    streak = service.get_current_streak(user_id=user.id)
    return {"streak": streak}

@app.get("/api/stats/history", response_model=List[DailyStats])
def get_history(start: date, end: date, user: UserIdentity = Depends(get_current_user)):
    return service.get_stats_history(start, end, user_id=user.id)

@app.get("/api/settings/goals", response_model=GoalSettings)
def get_goal_settings(user: UserIdentity = Depends(get_current_user)):
    return service.get_goal_settings(user_id=user.id)

@app.put("/api/settings/goals", response_model=GoalSettings)
def put_goal_settings(settings: GoalSettings, user: UserIdentity = Depends(get_current_user)):
    return service.save_goal_settings(user_id=user.id, settings=settings)


@app.get("/api/me", response_model=UserIdentity)
def get_me(user: UserIdentity = Depends(get_current_user)):
    return user


@app.get("/api/settings/api-keys", response_model=List[APIKeyRecord])
def list_api_keys(user: UserIdentity = Depends(get_current_user)):
    return service.list_api_keys(user.id)


@app.post("/api/settings/api-keys", response_model=APIKeyCreateResponse)
def create_api_key(payload: APIKeyCreateRequest, user: UserIdentity = Depends(get_current_user)):
    record, raw_key = service.create_api_key(
        user_id=user.id,
        name=payload.name,
        expires_in_days=payload.expires_in_days,
    )
    return APIKeyCreateResponse(
        id=record.id,
        name=record.name,
        api_key=raw_key,
        key_prefix=record.key_prefix,
    )


@app.delete("/api/settings/api-keys/{key_id}")
def revoke_api_key(key_id: int, user: UserIdentity = Depends(get_current_user)):
    if not service.revoke_api_key(user_id=user.id, key_id=key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success"}


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

def _auth(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[int]:
    token = _extract_api_key(authorization=authorization, x_api_key=x_api_key)
    if token:
        auth = service.authenticate_api_key(token)
        if not auth:
            raise HTTPException(status_code=403, detail="Invalid API key")
        _, user_id = auth
        return user_id
    if AUTH_TOKEN:
        if authorization and authorization.startswith("Bearer "):
            legacy = authorization.removeprefix("Bearer ").strip()
            if legacy == AUTH_TOKEN:
                return None
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return None

@app.get("/v1/widget/today")
def widget_today(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Get cached widget data.
    This endpoint does NO DB calls.
    It reads from the JSON cache file or memory.
    """
    user_id = _auth(authorization, x_api_key)
    if user_id is None:
        data = _load_cache_if_changed()
        return JSONResponse(content=data)

    today = date.today()
    day_stats = service.get_daily_summary(today, user_id=user_id)
    week_start = today - timedelta(days=6)
    week_history = service.get_stats_history(week_start, today, user_id=user_id)
    week_stats = {
        "total_kcal": sum(d.total_kcal for d in week_history),
        "total_protein": sum(d.total_protein for d in week_history),
        "total_carbs": sum(d.total_carbs for d in week_history),
        "total_fat": sum(d.total_fat for d in week_history),
        "days_tracked": len(week_history),
    }
    payload = {
        "generated_at": datetime.now().isoformat(),
        "timezone": "Europe/Berlin",
        "day": day_stats.model_dump(mode="json"),
        "week": week_stats,
        "streak": service.get_current_streak(user_id=user_id),
    }
    return JSONResponse(content=payload)
