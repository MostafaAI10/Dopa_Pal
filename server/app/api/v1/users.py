from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# Schema for updating settings
class UserSettingsUpdate(BaseModel):
    language: Optional[str] = None
    # Add other settings here if needed

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
        
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Settings updated",
        "language": user.language
    }
