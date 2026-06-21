from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any
from app.core.database import get_db
from app.models.reward import Reward
from app.api.v1.tasks import get_or_create_default_user

router = APIRouter()

class RewardResponse(BaseModel):
    id: int
    type: str
    unlocked_at: datetime
    metadata_json: Optional[Any]

    class Config:
        from_attributes = True

@router.get("/rewards/unlocked", response_model=List[RewardResponse])
def get_unlocked_rewards(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    # Fetch theme configurations
    rewards = db.query(Reward).filter(
        Reward.user_id == user.id
    ).order_by(Reward.unlocked_at.desc()).all()
    return rewards

@router.get("/rewards/vault", response_model=List[RewardResponse])
def get_interest_vault_drops(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    # Fetch interest drops specifically
    drops = db.query(Reward).filter(
        Reward.user_id == user.id,
        Reward.type == "interest_drop"
    ).order_by(Reward.unlocked_at.desc()).all()
    return drops
