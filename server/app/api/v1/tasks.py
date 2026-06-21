"""
Task and bubble API endpoints.

All NLP/AI logic is delegated to ``task_service`` → ``AIService``.
These routes handle HTTP concerns only: request validation, response
shaping, WebSocket broadcasting, and error mapping.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional
from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.services import task_service, reward_service
from app.services.websocket_manager import manager as ws_manager

router = APIRouter()


# ---------- Schemas ----------

class TaskIngestRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Raw text to parse via NLP pipeline")
    source_type: str = Field(..., description="'highlight', 'voice', 'manual', 'calendar'")


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    deadline: datetime
    estimated_hours: float = Field(..., gt=0, le=200)
    interest_tag: Optional[str] = None
    source_type: str = "manual"


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    deadline: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    pinch_score: Optional[float] = None


class SubBlockResponse(BaseModel):
    id: int
    sequence: int
    duration_minutes: int
    scheduled_date: date
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
    pinch_score: Optional[float] = None
    sub_blocks: List[SubBlockResponse]

    class Config:
        from_attributes = True


def get_or_create_default_user(db: Session) -> User:
    """Mock/session default user for the ambient runner."""
    user = db.query(User).first()
    if not user:
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


# ---------- Task Endpoints ----------

@router.post("/tasks/ingest", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def api_ingest_task(payload: TaskIngestRequest, db: Session = Depends(get_db)):
    """
    NLP-powered task ingestion: parses raw text through the AI pipeline
    (date extraction, effort estimation, interest tagging, chunking, PINCH scoring),
    then persists the structured result.
    """
    user = get_or_create_default_user(db)

    try:
        task = task_service.ingest_from_raw_text(
            db=db,
            user_id=user.id,
            raw_text=payload.source_text,
            source_type=payload.source_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Broadcast task creation to connected clients
    await ws_manager.publish(user.id, "task_ingested", {
        "task_id": task.id,
        "title": task.title,
        "pinch_score": task.pinch_score,
        "sub_block_count": len(task.sub_blocks),
    })

    return task


@router.post("/tasks/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def api_create_task(payload: TaskCreateRequest, db: Session = Depends(get_db)):
    """
    Structured task creation: accepts pre-filled fields (no NLP parsing),
    but still uses the AI module for chunking and PINCH scoring.
    """
    user = get_or_create_default_user(db)

    task = task_service.create_manual_task(
        db=db,
        user_id=user.id,
        title=payload.title,
        deadline=payload.deadline,
        estimated_hours=payload.estimated_hours,
        interest_tag=payload.interest_tag,
        source_type=payload.source_type,
    )

    await ws_manager.publish(user.id, "task_ingested", {
        "task_id": task.id,
        "title": task.title,
        "pinch_score": task.pinch_score,
        "sub_block_count": len(task.sub_blocks),
    })

    return task


@router.get("/tasks", response_model=List[TaskResponse])
def api_get_tasks(db: Session = Depends(get_db)):
    """Returns all tasks for the current user."""
    user = get_or_create_default_user(db)
    tasks = db.query(Task).filter(Task.user_id == user.id).order_by(Task.created_at.desc()).all()
    return tasks


@router.post("/tasks/{task_id}/complete")
def api_complete_task(task_id: int, db: Session = Depends(get_db)):
    """Marks an entire task as completed."""
    user = get_or_create_default_user(db)
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = "completed"
    db.commit()
    
    return {"message": "Task completed successfully"}

@router.delete("/tasks/{task_id}")
def api_delete_task(task_id: int, db: Session = Depends(get_db)):
    """Deletes a task."""
    user = get_or_create_default_user(db)
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}

@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def api_update_task(task_id: int, payload: TaskUpdateRequest, db: Session = Depends(get_db)):
    """Updates a task."""
    user = get_or_create_default_user(db)
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if payload.title is not None:
        task.title = payload.title
    if payload.deadline is not None:
        task.deadline = payload.deadline
    if payload.estimated_hours is not None:
        task.estimated_hours = payload.estimated_hours
    if payload.pinch_score is not None:
        task.pinch_score = payload.pinch_score
        
    db.commit()
    db.refresh(task)
    return task


@router.post("/sub-blocks/{sub_block_id}/complete")
async def api_complete_sub_block(sub_block_id: int, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    result = reward_service.complete_sub_block(db, user.id, sub_block_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Broadcast completion event
    await ws_manager.publish(user.id, "block_completed", {
        "sub_block_id": sub_block_id,
        "task_completed": result.get("task_completed", False),
        "unlocked_theme": result.get("unlocked_theme"),
        "interest_vault_fact": result.get("interest_vault_fact"),
    })

    return result


# ---------- Bubble Endpoint ----------

@router.get("/bubble/next")
def api_get_next_bubble(db: Session = Depends(get_db)):
    """
    Returns the next task bubble for the user, ranked by the PINCH engine
    using today's cognitive state score for energy-aware prioritisation.

    Response includes a primary block and optional bonus blocks (only shown
    when state_score >= 50, per Design Rule #1).
    """
    user = get_or_create_default_user(db)

    last_log = db.query(StateLog).filter(
        StateLog.user_id == user.id
    ).order_by(StateLog.id.desc()).first()
    state_score = last_log.computed_state_score if last_log else 75.0

    scored_blocks = task_service.get_ranked_pending_blocks(db, user.id, state_score)

    if not scored_blocks:
        return {
            "state_score": state_score,
            "mode": "calm",
            "primary_block": None,
            "bonus_blocks": [],
        }

    primary_block, primary_score = scored_blocks[0]
    bonus_blocks = []

    if state_score >= 50.0 and len(scored_blocks) > 1:
        for sb, _score in scored_blocks[1:3]:
            bonus_blocks.append({
                "sub_block_id": sb.id,
                "task_title": sb.task.title,
                "duration_minutes": sb.duration_minutes,
                "pinch_score": round(_score, 2),
            })

    mode = "focused" if state_score >= 50.0 else "chill"

    return {
        "state_score": state_score,
        "mode": mode,
        "primary_block": {
            "sub_block_id": primary_block.id,
            "task_title": primary_block.task.title,
            "duration_minutes": primary_block.duration_minutes,
            "pinch_score": round(primary_score, 2),
            "interest_tag": primary_block.task.interest_tag,
        },
        "bonus_blocks": bonus_blocks,
    }


# ---------- AI Summary Endpoint ----------

@router.get("/bubble/summary")
def api_get_ai_summary(db: Session = Depends(get_db)):
    """
    Returns an AI-generated motivational summary of remaining tasks.
    """
    user = get_or_create_default_user(db)
    pending_tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.status == "pending"
    ).all()

    if not pending_tasks:
        return {"text": "أنت بطل! 🌟 لقد أنهيت كل مهامك لليوم. استرح الآن واستمتع بجرعة الدوبامين! 🧠✨"}
    
    task_count = len(pending_tasks)
    titles = [t.title for t in pending_tasks[:2]]
    
    names_str = " و ".join(titles)
    if task_count > 2:
        names_str += f" و {task_count - 2} مهام أخرى"

    messages = [
        f"أهلاً بك! 🔥 أمامك {task_count} مهام متبقية. أهمها الآن: {names_str}. أنا أثق بقدراتك، لننطلق وندمر هذه المهام! 💪",
        f"مرحباً يا بطل! 🧠 لديك {task_count} مهام تنتظر إنجازك، مثل {names_str}. كل مهمة تنهيها ستعطيك جرعة رائعة من الدوبامين. ابدأ الآن! 🚀",
        f"وقت التركيز! ⚡ باقي {task_count} مهام لليوم. ركز على {names_str} وستشعر بإنجاز عظيم. أنا هنا لدعمك! 🎯"
    ]
    
    import random
    return {"text": random.choice(messages)}

# ---------- WebSocket Endpoint ----------

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; client can send pings or commands
            data = await websocket.receive_text()
            # Echo acknowledgment — extensible for client-to-server commands
            await websocket.send_text(f'{{"event":"ack","data":{{"received":true}}}}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
