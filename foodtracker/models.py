from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field

class Entry(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    title: str
    serving_amount: float = Field(default=1.0, gt=0)
    kcal: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    
    entry_date: date = Field(..., description="DD.MM.YYYY")
    entry_time: time = Field(..., description="HH:MM")
    
    @property
    def ts_local(self) -> str:
        return f"{self.entry_date.isoformat()}T{self.entry_time.isoformat()}"

    @property
    def timestamp(self) -> datetime:
        return datetime.combine(self.entry_date, self.entry_time)

class DailyStats(BaseModel):
    date: date
    total_kcal: float
    total_protein: float
    total_carbs: float
    total_fat: float
    entry_count: int


class GoalSettings(BaseModel):
    body_weight_kg: float = Field(default=80.0, gt=0)
    weight_loss_per_week_kg: float = Field(default=0.3, ge=0)


class UserIdentity(BaseModel):
    id: int
    email: str
    is_admin: bool = False
    is_active: bool = True


class APIKeyRecord(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class APIKeyCreateRequest(BaseModel):
    name: str = Field(default="OpenClaw")
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    api_key: str
    key_prefix: str


class UserUpsertRequest(BaseModel):
    email: str
    is_admin: bool = False
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
