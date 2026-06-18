from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.services import task_service, reward_service

router = APIRouter()

# Schemas
class TaskIngestRequest(BaseModel):
    source_text: str
    source_type: str # 'highlight', 'voice', 'manual', 'calendar'

class TaskCreateRequest(BaseModel):
    title: str
    deadline: datetime
    estimated_hours: float
    interest_tag: Optional[str] = None
    source_type: str = "manual"

class SubBlockResponse(BaseModel):
    sequence: int
    duration_minutes: int
    scheduled_date: str
    status: str

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: int
    title: str
    deadline: datetime
    estimated_hours: float
    interest_tag: Optional[str]
    status: str
    sub_blocks: List[SubBlockResponse]

    class Config:
        from_attributes = True

def get_or_create_default_user(db: Session) -> User:
    """Helper to mock/session default user for the ambient runner."""
    user = db.query(User).first()
    if not user:
        # Create a default user
        from datetime import time
        user = User(
            email="default_user@dopapal.app",
            name="Default User",
            wake_time_pref=time(7, 30)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/tasks/ingest", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def api_ingest_task(payload: TaskIngestRequest, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    # 1. Deterministically parse the raw input text
    parsed = task_service.parse_raw_text(payload.source_text)
    
    # 2. Ingest parsed task
    task = task_service.ingest_task(
        db=db,
        user_id=user.id,
        title=parsed["title"],
        raw_source_text=payload.source_text,
        source_type=payload.source_type,
        deadline=parsed["deadline"],
        estimated_hours=parsed["estimated_hours"],
        interest_tag=parsed["interest_tag"]
    )
    
    # Format dates to string for response validation
    # response schema is populated automatically from task.sub_blocks
    return task

@router.post("/tasks/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def api_create_task(payload: TaskCreateRequest, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    task = task_service.ingest_task(
        db=db,
        user_id=user.id,
        title=payload.title,
        raw_source_text=None,
        source_type=payload.source_type,
        deadline=payload.deadline,
        estimated_hours=payload.estimated_hours,
        interest_tag=payload.interest_tag
    )
    return task

@router.post("/tasks/{sub_block_id}/complete")
def api_complete_sub_block(sub_block_id: int, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    result = reward_service.complete_sub_block(db, user.id, sub_block_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/bubble/next")
def api_get_next_bubble(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    # 1. Fetch current/last state log score, default to 75.0 if no logs today
    last_log = db.query(StateLog).filter(
        StateLog.user_id == user.id
    ).order_by(StateLog.id.desc()).first()
    state_score = last_log.computed_state_score if last_log else 75.0
    
    # 2. Fetch pending sub-blocks of active tasks
    pending_blocks = db.query(SubBlock).join(Task).filter(
        Task.user_id == user.id,
        Task.status == "pending",
        SubBlock.status == "pending"
    ).all()
    
    if not pending_blocks:
        return {
            "state_score": state_score,
            "mode": "calm",
            "primary_block": None,
            "bonus_blocks": []
        }
        
    # 3. Sort sub-blocks by PINCH score of parent task
    # We evaluate Priority = Urgency * 0.6 + Novelty * 0.2 + Challenge * 0.2
    scored_blocks = []
    for sb in pending_blocks:
        score = task_service.calculate_pinch_score(sb.task, state_score)
        scored_blocks.append((sb, score))
        
    # Sort descending by priority score
    scored_blocks.sort(key=lambda x: x[1], reverse=True)
    
    primary_block = scored_blocks[0][0]
    bonus_blocks = []
    
    # Unlock up to 2 optional bonus items if state score is high (>= 50)
    if state_score >= 50.0 and len(scored_blocks) > 1:
        for sb, score in scored_blocks[1:3]:
            bonus_blocks.append({
                "sub_block_id": sb.id,
                "task_title": sb.task.title,
                "duration_minutes": sb.duration_minutes
            })
            
    mode = "focused" if state_score >= 50.0 else "chill"
    
    return {
        "state_score": state_score,
        "mode": mode,
        "primary_block": {
            "sub_block_id": primary_block.id,
            "task_title": primary_block.task.title,
            "duration_minutes": primary_block.duration_minutes,
            "context_hint": f"Open associated files or source for interest: {primary_block.task.interest_tag or 'N/A'}"
        },
        "bonus_blocks": bonus_blocks
    }
