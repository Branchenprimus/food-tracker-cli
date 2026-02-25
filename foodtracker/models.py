from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field

class Entry(BaseModel):
    id: Optional[int] = None
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
