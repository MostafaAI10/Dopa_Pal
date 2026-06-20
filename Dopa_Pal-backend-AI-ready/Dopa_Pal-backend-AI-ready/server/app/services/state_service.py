from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.state import StateLog
from app.models.task import SubBlock, Task

def get_completion_rate_48h(db: Session, user_id: int) -> float:
    """
    Calculates sub-block completion rate over the last 48 hours.
    """
    cutoff = datetime.utcnow() - timedelta(days=2)
    
    # Query all sub-blocks of the user scheduled in the last 48 hours
    # Join with tasks to filter by user_id
    total_blocks = db.query(SubBlock).join(Task).filter(
        Task.user_id == user_id,
        SubBlock.scheduled_date >= cutoff.date()
    ).count()
    
    if total_blocks == 0:
        return 1.0 # Default to full completion if no tasks were scheduled
        
    completed_blocks = db.query(SubBlock).join(Task).filter(
        Task.user_id == user_id,
        SubBlock.scheduled_date >= cutoff.date(),
        SubBlock.status == "completed"
    ).count()
    
    return float(completed_blocks) / total_blocks

def calculate_state_score_from_metrics(
    startup_delta_mins: int,
    mood_score: int,
    completion_rate_48h: float,
    early_actions: int
) -> float:
    """
    Mathematical state score logic.
    """
    # Scale components down to normalized weights
    normalized_delta = max(0.0, 1.0 - (startup_delta_mins / 120.0)) # penalize gaps up to 2 hours
    normalized_mood = (mood_score - 1) / 4.0 # Scales 1-5 down to 0.0-1.0
    normalized_actions = min(1.0, early_actions / 3.0) # caps at 3 actions
    
    state_score = (
        (0.35 * normalized_delta) +
        (0.30 * normalized_mood) +
        (0.25 * completion_rate_48h) +
        (0.10 * normalized_actions)
    ) * 100.0
    return round(state_score, 2)

def log_morning_state(
    db: Session,
    user_id: int,
    wake_time: Optional[datetime],
    startup_time: datetime,
    mood_score: int,
    early_actions: int = 0
) -> StateLog:
    # 1. Wake to startup delta calculation
    if wake_time:
        delta = (startup_time - wake_time).total_seconds() / 60.0
        startup_delta_mins = int(max(0, delta))
    else:
        startup_delta_mins = 0 # No penalty if wake time is unlogged
        
    # 2. Get historical 48h completion rate
    completion_rate = get_completion_rate_48h(db, user_id)
    
    # 3. Calculate score
    score = calculate_state_score_from_metrics(
        startup_delta_mins=startup_delta_mins,
        mood_score=mood_score,
        completion_rate_48h=completion_rate,
        early_actions=early_actions
    )
    
    # Create log entry
    log_entry = StateLog(
        user_id=user_id,
        date=date.today(),
        wake_time=wake_time,
        startup_time=startup_time,
        mood_score=mood_score,
        computed_state_score=score
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
