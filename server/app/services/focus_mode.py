"""
Focus mode service for dopaPal.

This service manages the focus mode functionality, which temporarily
dampens high-distraction vectors during critical startup windows to
preserve execution momentum.
"""

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from app.models.state import StateLog
from app.models.task import Task, SubBlock
from app.services.ai.service import AIService
from app.services.task_service import get_ai_service
from app.services.ai.schemas import PinchInput
from app.services.state_service import calculate_state_score_from_metrics


@dataclass
class FocusModeState:
    """Represents the state of focus mode."""
    is_active: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    priority_boost: float = 1.0  # Multiplier for task priority during focus mode


class FocusModeService:
    """Manages focus mode functionality for dopaPal."""
    
    def __init__(self):
        self._focus_state: FocusModeState = FocusModeState()
    
    def toggle_focus_mode(self, is_active: bool, duration_minutes: Optional[int] = None) -> FocusModeState:
        """
        Toggle focus mode on or off.
        
        Args:
            is_active: Whether to activate focus mode
            duration_minutes: Optional duration in minutes for focus mode
            
        Returns:
            Updated focus mode state
        """
        if is_active:
            self._focus_state.is_active = True
            self._focus_state.start_time = self._get_current_timestamp()
            if duration_minutes:
                self._focus_state.end_time = self._focus_state.start_time + (duration_minutes * 60.0)
        else:
            self._focus_state.is_active = False
            self._focus_state.end_time = None
        
        return self._focus_state
    
    def is_focus_mode_active(self) -> bool:
        """
        Check if focus mode is currently active.
        
        Returns:
            True if focus mode is active, False otherwise
        """
        if not self._focus_state.is_active:
            return False
        
        if self._focus_state.end_time:
            current_time = self._get_current_timestamp()
            return current_time < self._focus_state.end_time
        
        return True
    
    def get_focus_mode_priority_multiplier(self) -> float:
        """
        Get the priority multiplier to apply during focus mode.
        
        Returns:
            Priority multiplier (1.0 = normal, >1.0 = boost)
        """
        return self._focus_state.priority_boost if self.is_focus_mode_active() else 1.0
    
    def adjust_task_priority_for_focus_mode(
        self,
        db: Session,
        user_id: int,
        state_score: float
    ) -> list[tuple[SubBlock, float]]:
        """
        Adjust task priority based on focus mode state.
        
        Args:
            db: Database session
            user_id: User ID
            state_score: Current state score
            
        Returns:
            List of (sub_block, score) tuples ranked by priority
        """
        ai = get_ai_service()
        from datetime import datetime, timezone
        now_dt = datetime.now(timezone.utc)
        now = self._get_current_timestamp()
        
        # Fetch pending sub-blocks for the user
        pending_blocks = (
            db.query(SubBlock)
            .join(Task)
            .filter(
                Task.user_id == user_id,
                Task.status == "pending",
                SubBlock.status == "pending",
            )
            .all()
        )
        
        if not pending_blocks:
            return []
        
        # Build PinchInput for each sub-block's parent task
        candidates: dict[int, PinchInput] = {}
        block_map: dict[int, SubBlock] = {}
        
        for block in pending_blocks:
            task = block.task
            block_map[block.id] = block
            
            # Determine created_at — use task.created_at if available, else now_dt
            created_at = task.created_at if task.created_at else now_dt
            
            candidates[block.id] = PinchInput(
                deadline=task.deadline,
                created_at=created_at,
                interest_tag=task.interest_tag,
                user_interest_tags=[],  # TODO: load from user profile when implemented
                user_passion_tags=[],   # TODO: load from user profile when implemented
                is_novel=False,
                challenge_hint=None,
                estimated_hours=task.estimated_hours,
                raw_source_text=task.raw_source_text,
            )
        
        # Apply focus mode priority multiplier
        focus_multiplier = self.get_focus_mode_priority_multiplier()
        
        # Score and rank with focus mode adjustment
        ranked = ai.score_for_bubble(
            candidates=candidates,
            state_score=state_score,
            now=now_dt,
        )
        
        # Apply focus mode multiplier to scores
        scored_with_focus = []
        for block_id, breakdown in ranked:
            if block_id in block_map:
                adjusted_score = breakdown.total * focus_multiplier
                scored_with_focus.append((block_map[block_id], adjusted_score))
        
        # Sort by adjusted score
        scored_with_focus.sort(key=lambda x: x[1], reverse=True)
        
        return scored_with_focus
    
    def _get_current_timestamp(self) -> float:
        """
        Get current timestamp.
        
        Returns:
            Current timestamp as float
        """
        import time
        return time.time()


# Global service instance
focus_mode_service = FocusModeService()


def toggle_focus_mode(is_active: bool, duration_minutes: Optional[int] = None) -> FocusModeState:
    """
    Convenience function to toggle focus mode.
    
    Args:
        is_active: Whether to activate focus mode
        duration_minutes: Optional duration in minutes for focus mode
        
    Returns:
        Updated focus mode state
    """
    return focus_mode_service.toggle_focus_mode(is_active, duration_minutes)


def is_focus_mode_active() -> bool:
    """
    Convenience function to check if focus mode is active.
    
    Returns:
        True if focus mode is active, False otherwise
    """
    return focus_mode_service.is_focus_mode_active()


def adjust_task_priority_for_focus_mode(
    db: Session,
    user_id: int,
    state_score: float
) -> list[tuple[SubBlock, float]]:
    """
    Convenience function to adjust task priority based on focus mode.
    
    Args:
        db: Database session
        user_id: User ID
        state_score: Current state score
        
    Returns:
        List of (sub_block, score) tuples ranked by priority
    """
    return focus_mode_service.adjust_task_priority_for_focus_mode(db, user_id, state_score)
