"""
Task and bubble API endpoints.

All NLP/AI logic is delegated to ``task_service`` → ``AIService``.
These routes handle HTTP concerns only: request validation, response
shaping, WebSocket broadcasting, and error mapping.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.services import task_service, reward_service, focus_mode, enhanced_notification
from app.services.speech_to_text import speech_to_text_service
from app.services.websocket_manager import manager as ws_manager
from app.services.duration_parser import parse_duration, format_duration
from app.services.ai.schemas import SegmentationInput, SegmentationOutput
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tasks"])


# ---------- Schemas ----------

class TaskIngestRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Raw text to parse via NLP pipeline")
    source_type: str = Field(..., description="'highlight', 'voice', 'manual', 'calendar'")


class SegmentationRequest(BaseModel):
    """Mirrors SegmentationInput but with server-defaulted timestamp."""
    raw_input: str = Field(..., min_length=1, description="Raw chaotic text to segment")
    deadline_timestamp: Optional[datetime] = Field(None, description="ISO deadline")
    user_estimated_duration_minutes: Optional[int] = Field(None, gt=0, description="Estimated minutes")


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
    title: Optional[str] = None
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
    source_type: Optional[str] = None
    raw_source_text: Optional[str] = None
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

from app.services.speech_to_text import convert_audio_to_text  # Make sure this is imported

@router.post("/tasks/ingest", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def api_ingest_task(payload: TaskIngestRequest, db: Session = Depends(get_db)):
    """
    NLP-powered task ingestion: parses raw text through the AI pipeline.
    If the source_type is voice, it transcribes the base64 audio payload first.
    """
    # DEBUG TRACE: Raw payload inspection before any parsing
    source_text = payload.source_text
    total_len = len(source_text)
    first_100 = source_text[:100]
    last_100 = source_text[-100:] if total_len > 100 else source_text
    print(f"[INGEST-TRACE] source_text length={total_len} first_100={first_100!r} last_100={last_100!r}", flush=True)
    logger.info(f"[INGEST-TRACE] source_text length={total_len} first_100={first_100!r} last_100={last_100!r}")

    user = get_or_create_default_user(db)
    
    text_to_parse = payload.source_text

    # If it's a voice note, intercept and run the speech-to-text pipeline
    if payload.source_type == "voice":
        try:
            logger.info("Voice ingestion detected. Routing payload to Speech-to-Text Service...")
            text_to_parse = convert_audio_to_text(payload.source_text, source_type="voice")
        except ValueError as e:
            # Catch transcription failures (like UnknownValueError) and map to 422
            raise HTTPException(status_code=422, detail=str(e))

    try:
        task = task_service.ingest_from_raw_text(
            db=db,
            user_id=user.id,
            raw_text=text_to_parse,  # Passes the clean transcription string to NLP!
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


@router.post("/tasks/ingest-voice", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def api_ingest_voice_task(
    file: UploadFile = File(..., description="Raw binary voice recording file"),
    source_type: str = Form("voice"),
    db: Session = Depends(get_db)
):
    """
    Production-ready voice task ingestion endpoint.
    Streams raw binary media data directly, transcribes it, and routes to the NLP pipeline.
    """
    user = get_or_create_default_user(db)
    
    try:
        # Read the binary stream data directly out of the incoming file payload
        audio_bytes = await file.read()
        logger.info(f"📥 Received streaming multipart file. Size: {len(audio_bytes)} bytes")
        
        if not audio_bytes:
            raise HTTPException(status_code=422, detail="Uploaded file is empty.")

        # Pass the raw bytes straight to our updated speech-to-text logic
        transcribed_text = speech_to_text_service.audio_bytes_to_text(audio_bytes)
        
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))
    except Exception as err:
        logger.error(f"Failed to handle voice file stream processing: {str(err)}")
        raise HTTPException(status_code=500, detail="Internal server error handling media block.")

    # Route the transcribed clean string directly into your existing NLP service engine
    try:
        task = task_service.ingest_from_raw_text(
            db=db,
            user_id=user.id,
            raw_text=transcribed_text,
            source_type=source_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Broadcast task creation updates over websockets
    await ws_manager.publish(user.id, "task_ingested", {
        "task_id": task.id,
        "title": task.title,
        "pinch_score": task.pinch_score,
        "sub_block_count": len(task.sub_blocks),
    })

    return task

# ---------- Task Segmentation Endpoint ----------

@router.post("/tasks/segment", response_model=SegmentationOutput)
async def api_segment_task(payload: SegmentationRequest):
    """
    Task Segmentation Agent endpoint.

    Accepts raw, chaotic task input and returns a structured, multi-day
    execution plan with micro-steps, behavioral tips, and fog-of-war masking.
    This endpoint is stateless — it does NOT persist anything to the database.
    """
    ai = task_service.get_ai_service()

    segmentation_input = SegmentationInput(
        raw_input=payload.raw_input,
        current_timestamp=datetime.now(),
        deadline_timestamp=payload.deadline_timestamp,
        user_estimated_duration_minutes=payload.user_estimated_duration_minutes,
    )

    return ai.segment(segmentation_input)


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
                "block_title": sb.title,
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
            "block_title": primary_block.title,
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

# ---------- Duration Parser Endpoint ----------

class DurationParseRequest(BaseModel):
    duration: str = Field(..., description="Duration string to parse (e.g., '1.5 hours', '45 minutes', 'quick')")

class DurationParseResponse(BaseModel):
    hours: float = Field(..., description="Duration in hours")
    formatted: str = Field(..., description="Human-readable formatted duration")

@router.post("/parse-duration", response_model=DurationParseResponse)
def parse_duration_endpoint(request: DurationParseRequest):
    """
    Parse a duration string and convert it to hours.
    
    This endpoint provides a robust duration parser that can handle various
    natural language inputs for task duration estimation, making it much
    more flexible and user-friendly than the rigid string-matching approach
    used in the current implementation.
    
    Args:
        request: Duration string to parse
        
    Returns:
        Parsed duration in hours and formatted human-readable string
    """
    hours = parse_duration(request.duration)
    
    # Format the duration for display
    formatted = format_duration(hours)
    
    return DurationParseResponse(hours=hours, formatted=formatted)

# ---------- Focus Mode Endpoint ----------

class FocusModeToggleRequest(BaseModel):
    is_active: bool = Field(..., description="Whether to activate focus mode")
    duration_minutes: Optional[int] = Field(None, description="Optional duration in minutes for focus mode")

class FocusModeStateResponse(BaseModel):
    is_active: bool = Field(..., description="Whether focus mode is active")
    start_time: Optional[float] = Field(None, description="Focus mode start timestamp")
    end_time: Optional[float] = Field(None, description="Focus mode end timestamp")
    priority_boost: float = Field(..., description="Priority boost multiplier during focus mode")

@router.post("/focus-mode/toggle", response_model=FocusModeStateResponse)
def toggle_focus_mode_endpoint(request: FocusModeToggleRequest, db: Session = Depends(get_db)):
    """
    Toggle focus mode on or off.
    
    Args:
        request: Focus mode toggle request
        db: Database session
        
    Returns:
        Updated focus mode state
    """
    user = get_or_create_default_user(db)
    
    # Toggle focus mode
    focus_state = focus_mode.toggle_focus_mode(
        is_active=request.is_active,
        duration_minutes=request.duration_minutes
    )
    
    return FocusModeStateResponse(
        is_active=focus_state.is_active,
        start_time=focus_state.start_time,
        end_time=focus_state.end_time,
        priority_boost=focus_state.priority_boost
    )

@router.get("/focus-mode/state", response_model=FocusModeStateResponse)
def get_focus_mode_state_endpoint(db: Session = Depends(get_db)):
    """
    Get the current focus mode state.
    
    Args:
        db: Database session
        
    Returns:
        Current focus mode state
    """
    user = get_or_create_default_user(db)
    
    # Get current focus mode state
    focus_state = focus_mode.focus_mode_service._focus_state
    
    return FocusModeStateResponse(
        is_active=focus_state.is_active,
        start_time=focus_state.start_time,
        end_time=focus_state.end_time,
        priority_boost=focus_state.priority_boost
    )

# ---------- Enhanced Notification Endpoint ----------

class EnhancedNotificationRequest(BaseModel):
    type: enhanced_notification.NotificationType = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    icon: Optional[str] = Field(None, description="Notification icon")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Notification actions")
    audio_type: Optional[str] = Field(None, description="Audio type for feedback")
    priority: str = Field("normal", description="Notification priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Notification metadata")

@router.post("/notifications/enhanced", response_model=dict)
def create_enhanced_notification_endpoint(request: EnhancedNotificationRequest, db: Session = Depends(get_db)):
    """
    Create an enhanced notification with audio feedback.
    
    Args:
        request: Enhanced notification request
        db: Database session
        
    Returns:
        Created notification
    """
    user = get_or_create_default_user(db)
    
    # Parse actions
    parsed_actions = None
    if request.actions:
        parsed_actions = [enhanced_notification.NotificationAction(**a) for a in request.actions]
    
    # Create enhanced notification
    notification = enhanced_notification.create_enhanced_notification(
        notification_type=request.type,
        title=request.title,
        body=request.body,
        icon=request.icon,
        actions=parsed_actions,
        audio_type=request.audio_type,
        priority=request.priority,
        metadata=request.metadata
    )
    
    return {
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "icon": notification.icon,
        "audio_file": notification.audio_file,
        "priority": notification.priority,
        "timestamp": notification.timestamp,
        "metadata": notification.metadata
    }

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
