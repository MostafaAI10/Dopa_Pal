from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import time

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# Schema for updating settings
class UserSettingsUpdate(BaseModel):
    language: Optional[str] = None
    name: Optional[str] = None
    wake_time_pref: Optional[str] = None

@router.get("/user/settings")
def get_user_settings(db: Session = Depends(get_db)):
    # Since we don't have auth yet, fetch the first user (default user)
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "language": user.language,
        "name": user.name,
        "wake_time_pref": user.wake_time_pref.isoformat() if user.wake_time_pref else None
    }

@router.patch("/user/settings")
def update_user_settings(settings: UserSettingsUpdate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if settings.language is not None:
        user.language = settings.language
    if settings.name is not None:
        user.name = settings.name
    if settings.wake_time_pref is not None:
        try:
            hours, minutes = settings.wake_time_pref.split(":", 1)
            user.wake_time_pref = time(int(hours), int(minutes))
        except Exception:
            raise HTTPException(status_code=422, detail="wake_time_pref must use HH:MM format")
        
    db.commit()
    db.refresh(user)

    return {
        "message": "Settings updated",
        "language": user.language
    }
