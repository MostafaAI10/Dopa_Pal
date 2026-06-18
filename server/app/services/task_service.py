import re
import math
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task import Task, SubBlock

def parse_raw_text(text: str) -> dict:
    """
    Deterministic regex-based parsing to extract Title, Deadline, Effort, and Interest
    from unstructured source texts (e.g. highlight tasks, voice dumps).
    """
    # 1. Clean Title Extraction: take first clause, strip typical prompts
    cleaned_title = text.strip()
    for prefix in ["Need to ", "need to ", "I need to ", "i need to ", "Complete ", "complete "]:
        if cleaned_title.lower().startswith(prefix.lower()):
            cleaned_title = cleaned_title[len(prefix):]
    
    if "," in cleaned_title:
        cleaned_title = cleaned_title.split(",")[0]
    elif "." in cleaned_title:
        cleaned_title = cleaned_title.split(".")[0]
        
    cleaned_title = cleaned_title.strip()
    if len(cleaned_title) > 60:
        cleaned_title = cleaned_title[:57] + "..."
        
    # Make sure title is capitalized
    cleaned_title = cleaned_title[0].upper() + cleaned_title[1:] if cleaned_title else "New Task"

    # 2. Extract Deadline (fallback to 7 days)
    deadline = datetime.utcnow() + timedelta(days=7)
    today = datetime.utcnow()
    text_lower = text.lower()
    
    if "next friday" in text_lower:
        days_ahead = 4 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        deadline = (today + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
    elif "tomorrow" in text_lower:
        deadline = (today + timedelta(days=1)).replace(hour=17, minute=0, second=0)
    elif "friday" in text_lower:
        days_ahead = 4 - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        deadline = (today + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
        
    # 3. Extract Estimated Hours (fallback to 2.0)
    hours = 2.0
    hour_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?', text_lower)
    if hour_match:
        hours = float(hour_match.group(1))

    # 4. Extract Interest Tag
    interest_tag = None
    keywords = {
        "architecture": ["architecture", "design", "specification", "blueprint"],
        "cybersecurity": ["security", "cybersecurity", "encryption", "auth", "login"],
        "german": ["german", "vocabulary", "language"]
    }
    for tag, keys in keywords.items():
        if any(k in text_lower for k in keys):
            interest_tag = tag
            break

    return {
        "title": cleaned_title,
        "deadline": deadline,
        "estimated_hours": hours,
        "interest_tag": interest_tag
    }

def ingest_task(
    db: Session,
    user_id: int,
    title: str,
    raw_source_text: Optional[str],
    source_type: str,
    deadline: datetime,
    estimated_hours: float,
    interest_tag: Optional[str] = None
) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        raw_source_text=raw_source_text,
        source_type=source_type,
        deadline=deadline,
        estimated_hours=estimated_hours,
        interest_tag=interest_tag,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Trigger chunking immediately
    chunk_task(db, task)
    return task

def chunk_task(db: Session, task: Task) -> List[SubBlock]:
    # Delete existing subblocks if any (failsafe)
    db.query(SubBlock).filter(SubBlock.task_id == task.id).delete()
    
    duration_per_block = 120 # 2 hours in minutes
    total_minutes = task.estimated_hours * 60
    num_blocks = max(1, math.ceil(total_minutes / duration_per_block))
    
    # Calculate spacing
    today = date.today()
    deadline_date = task.deadline.date()
    total_days = (deadline_date - today).days
    
    sub_blocks = []
    if total_days <= 1:
        # If deadline is today or tomorrow, schedule all blocks immediately
        for i in range(num_blocks):
            sub_block = SubBlock(
                task_id=task.id,
                sequence=i + 1,
                duration_minutes=duration_per_block,
                scheduled_date=today,
                status="pending"
            )
            db.add(sub_block)
            sub_blocks.append(sub_block)
    else:
        # Drip-feed pacing: distribute blocks evenly across the timeline
        # Avoid clustering at the cutoff
        interval = max(1, total_days // num_blocks)
        for i in range(num_blocks):
            # Cap the scheduled date at the day before the deadline
            offset_days = min(i * interval, total_days - 1)
            scheduled_date = today + timedelta(days=offset_days)
            
            sub_block = SubBlock(
                task_id=task.id,
                sequence=i + 1,
                duration_minutes=duration_per_block,
                scheduled_date=scheduled_date,
                status="pending"
            )
            db.add(sub_block)
            sub_blocks.append(sub_block)
            
    db.commit()
    return sub_blocks

def recalculate_schedule(db: Session, user_id: int, start_date: date) -> None:
    """
    Reflow remaining sub-blocks for skipped or missed days without shame triggers.
    Spreads pending subblocks of active tasks starting from start_date.
    """
    # Fetch all tasks of the user that are still pending
    active_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status == "pending"
    ).all()
    
    for task in active_tasks:
        # Fetch remaining pending subblocks for this task
        pending_blocks = db.query(SubBlock).filter(
            SubBlock.task_id == task.id,
            SubBlock.status == "pending",
            SubBlock.scheduled_date >= start_date
        ).order_by(SubBlock.sequence).all()
        
        if not pending_blocks:
            continue
            
        deadline_date = task.deadline.date()
        total_days_remaining = (deadline_date - start_date).days
        
        if total_days_remaining <= 1:
            # Shift everything to start_date
            for block in pending_blocks:
                block.scheduled_date = start_date
        else:
            interval = max(1, total_days_remaining // len(pending_blocks))
            for idx, block in enumerate(pending_blocks):
                offset_days = min(idx * interval, total_days_remaining - 1)
                block.scheduled_date = start_date + timedelta(days=offset_days)
                
    db.commit()

def calculate_pinch_score(task: Task, current_state_score: float) -> float:
    """
    Blends deadline urgency with PINCH framework metrics:
    Priority Score = (Urgency Weight * 0.6) + (Novelty Weight * 0.2) + (Challenge Match * 0.2)
    """
    today = date.today()
    deadline_date = task.deadline.date()
    days_left = (deadline_date - today).days
    
    # 1. Urgency: higher score when closer to deadline (capped between 0 and 1)
    if days_left <= 0:
        urgency = 1.0
    else:
        # Baseline urgency scale over a 30-day window
        urgency = max(0.0, min(1.0, 1.0 - (days_left / 30.0)))
        
    # 2. Novelty: Task added recently or featuring high curiosity tags
    # Let's say high novelty if it has interest tags
    novelty = 1.0 if task.interest_tag else 0.5
    
    # 3. Challenge Match:
    # If state score is low, high challenge tasks are penalized (reduced priority) to avoid paralysis
    # If state score is high, high challenge tasks are promoted
    is_high_effort = task.estimated_hours >= 4.0
    if current_state_score >= 50.0:
        challenge = 1.0 if is_high_effort else 0.6
    else:
        challenge = 0.3 if is_high_effort else 1.0 # low-energy days prefer low-friction tasks
        
    priority_score = (urgency * 0.6) + (novelty * 0.2) + (challenge * 0.2)
    return round(priority_score * 100, 2)
