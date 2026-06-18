from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from app.core.database import get_db
from app.models.state import StateLog
from app.services import state_service, task_service
from app.api.v1.tasks import get_or_create_default_user

router = APIRouter()

class StateLogCreate(BaseModel):
    wake_time: Optional[datetime] = None
    startup_time: datetime = Field(default_factory=datetime.utcnow)
    mood_score: int = Field(..., ge=1, le=5)
    early_actions: int = 0

class StateLogResponse(BaseModel):
    id: int
    date: date
    wake_time: Optional[datetime]
    startup_time: datetime
    mood_score: int
    computed_state_score: float

    class Config:
        from_attributes = True

@router.post("/state/log", response_model=StateLogResponse)
def log_user_state(payload: StateLogCreate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    # 1. Check if state was already logged today
    today = date.today()
    existing = db.query(StateLog).filter(
        StateLog.user_id == user.id,
        StateLog.date == today
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="State score has already been logged for today."
        )
        
    # 2. Log state and calculate score
    state_log = state_service.log_morning_state(
        db=db,
        user_id=user.id,
        wake_time=payload.wake_time,
        startup_time=payload.startup_time,
        mood_score=payload.mood_score,
        early_actions=payload.early_actions
    )
    
    # 3. Automatically trigger failure-neutral scheduling reflow
    # Recalculate schedule starting from today so that missed tasks flow forward neutrally
    task_service.recalculate_schedule(db, user.id, today)
    
    return state_log

@router.get("/state/logs", response_model=List[StateLogResponse])
def get_user_state_logs(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    logs = db.query(StateLog).filter(
        StateLog.user_id == user.id
    ).order_by(StateLog.date.desc()).all()
    return logs
