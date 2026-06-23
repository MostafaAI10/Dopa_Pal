from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any, Dict
from app.core.database import get_db
from app.models.reward import Reward
from app.api.v1.tasks import get_or_create_default_user

router = APIRouter(tags=["Rewards"])

class RewardResponse(BaseModel):
    id: int
    type: str
    unlocked_at: datetime
    metadata_json: Optional[Any] = None

    class Config:
        from_attributes = True

class PurchaseRequest(BaseModel):
    type: str = Field(..., pattern=r"^(theme|shop_item|interest_drop)$")
    item_id: str = Field(..., min_length=1, description="e.g. 'ocean', 'music-lofi'")
    metadata: Optional[Dict[str, Any]] = None

@router.get("/rewards/unlocked", response_model=List[RewardResponse])
def get_unlocked_rewards(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    # Fetch theme configurations
    rewards = db.query(Reward).filter(
        Reward.user_id == user.id
    ).order_by(Reward.unlocked_at.desc()).all()
    return rewards

_INITIAL_VAULT_FACTS = [
    {"tag": "cybersecurity", "fact": "Multi-factor authentication (MFA) blocks 99.9% of automated account takeover attacks."},
    {"tag": "neuroscience", "fact": "Dopamine isn't just about pleasure—it's primarily about anticipation and motivation."},
    {"tag": "programming", "fact": "The first computer virus was created in 1986 and was called 'Brain'."},
]

@router.get("/rewards/vault", response_model=List[RewardResponse])
def get_interest_vault_drops(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    drops = db.query(Reward).filter(
        Reward.user_id == user.id,
        Reward.type == "interest_drop"
    ).order_by(Reward.unlocked_at.desc()).all()

    if not drops:
        for fact in _INITIAL_VAULT_FACTS:
            db.add(Reward(
                user_id=user.id,
                type="interest_drop",
                metadata_json=fact,
            ))
        db.commit()
        drops = db.query(Reward).filter(
            Reward.user_id == user.id,
            Reward.type == "interest_drop"
        ).order_by(Reward.unlocked_at.desc()).all()

    return drops

@router.post("/rewards/purchase", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
def purchase_reward(payload: PurchaseRequest, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    reward = Reward(
        user_id=user.id,
        type=payload.type,
        metadata_json=payload.metadata or {"item_id": payload.item_id},
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward
