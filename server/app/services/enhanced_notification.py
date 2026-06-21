"""
Enhanced notification system with audio feedback for dopaPal.

This service provides enhanced notification capabilities with audio feedback,
task-specific actions, and integration with the focus mode system.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI
from app.core.config import settings
from app.services.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    HIGH_PRIORITY = "high_priority"
    DAILY_REMINDER = "daily_reminder"
    COMPLETION_SUCCESS = "completion_success"
    FOCUS_MODE_ENTERED = "focus_mode_entered"
    FOCUS_MODE_EXITED = "focus_mode_exited"
    INTEREST_VAULT_DROP = "interest_vault_drop"
    REWARD_UNLOCKED = "reward_unlocked"


@dataclass
class NotificationAction:
    """Represents an action that can be taken on a notification."""
    type: str
    label: str
    action: str
    icon: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class EnhancedNotification:
    """Enhanced notification with audio feedback and actions."""
    id: str
    type: NotificationType
    title: str
    body: str
    icon: Optional[str] = None
    actions: Optional[List[NotificationAction]] = None
    audio_file: Optional[str] = None
    priority: str = "normal"  # normal, high, urgent
    timestamp: float = None
    metadata: Optional[Dict[str, Any]] = None


class AudioFeedbackService:
    """Service for providing audio feedback for notifications."""
    
    def __init__(self):
        self._audio_cache: Dict[str, Any] = {}
        self._is_supported = self._check_audio_support()
    
    def _check_audio_support(self) -> bool:
        """Check if audio playback is supported in the current environment."""
        try:
            import audioop
            return True
        except ImportError:
            return False
    
    async def play_notification_sound(self, sound_type: str, volume: float = 0.5) -> None:
        """
        Play a notification sound.
        
        Args:
            sound_type: Type of sound to play (e.g., 'success', 'warning', 'urgent')
            volume: Volume level (0.0 to 1.0)
        """
        if not self._is_supported:
            return
        
        # Generate or retrieve audio buffer for the sound type
        audio_buffer = await self._get_or_generate_audio(sound_type)
        
        # Play the audio
        # In Electron, this would use the native audio system
        # In web, this would use the Web Audio API
        await self._play_audio_buffer(audio_buffer, volume)
    
    async def _get_or_generate_audio(self, sound_type: str) -> Any:
        """
        Get or generate audio buffer for a sound type.
        
        Args:
            sound_type: Type of sound
            
        Returns:
            Audio buffer
        """
        if sound_type not in self._audio_cache:
            self._audio_cache[sound_type] = await self._generate_audio(sound_type)
        
        return self._audio_cache[sound_type]
    
    async def _generate_audio(self, sound_type: str) -> Any:
        """
        Generate audio for a sound type.
        
        Args:
            sound_type: Type of sound
            
        Returns:
            Generated audio buffer
        """
        # This is a placeholder implementation
        # In production, this would use a proper audio generation library
        # or load pre-recorded sound files
        
        # For now, return a simple tone
        import numpy as np
        import asyncio
        
        # Generate a simple tone based on sound type
        frequency = self._get_frequency_for_sound_type(sound_type)
        duration = self._get_duration_for_sound_type(sound_type)
        sample_rate = 44100
        
        # Generate sine wave
        t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        return audio_data
    
    def _get_frequency_for_sound_type(self, sound_type: str) -> float:
        """
        Get frequency for a sound type.
        
        Args:
            sound_type: Type of sound
            
        Returns:
            Frequency in Hz
        """
        frequencies = {
            'success': 440.0,  # A4 note
            'warning': 220.0,  # A3 note
            'urgent': 880.0,   # A5 note
            'notification': 330.0,  # E4 note
        }
        return frequencies.get(sound_type, 440.0)
    
    def _get_duration_for_sound_type(self, sound_type: str) -> float:
        """
        Get duration for a sound type.
        
        Args:
            sound_type: Type of sound
            
        Returns:
            Duration in seconds
        """
        durations = {
            'success': 0.5,
            'warning': 0.8,
            'urgent': 1.0,
            'notification': 0.3,
        }
        return durations.get(sound_type, 0.5)
    
    async def _play_audio_buffer(self, audio_buffer: Any, volume: float) -> None:
        """
        Play an audio buffer.
        
        Args:
            audio_buffer: Audio buffer to play
            volume: Volume level
        """
        # This is a placeholder implementation
        # In production, this would use the native audio system
        # or Web Audio API for web clients
        
        # For now, just log the audio playback
        logger.debug("Playing audio buffer with volume: %s", volume)


class EnhancedNotificationService:
    """Service for managing enhanced notifications with audio feedback."""
    
    def __init__(self):
        self._audio_service = AudioFeedbackService()
        self._notification_history: List[EnhancedNotification] = []
        self._active_notifications: Dict[str, EnhancedNotification] = {}
    
    async def create_notification(
        self,
        notification_type: NotificationType,
        title: str,
        body: str,
        icon: Optional[str] = None,
        actions: Optional[List[NotificationAction]] = None,
        audio_type: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> EnhancedNotification:
        """
        Create an enhanced notification with audio feedback.
        
        Args:
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            icon: Optional icon
            actions: Optional notification actions
            audio_type: Optional audio type for feedback
            priority: Notification priority
            metadata: Optional metadata
            
        Returns:
            Created notification
        """
        import uuid
        import time
        
        notification_id = str(uuid.uuid4())
        timestamp = time.time()
        
        notification = EnhancedNotification(
            id=notification_id,
            type=notification_type,
            title=title,
            body=body,
            icon=icon,
            actions=actions,
            audio_file=audio_type,
            priority=priority,
            timestamp=timestamp,
            metadata=metadata
        )
        
        # Add to history
        self._notification_history.append(notification)
        
        # Play audio feedback if specified
        if audio_type:
            await self._audio_service.play_notification_sound(audio_type)
        
        # Broadcast notification via WebSocket
        await self._broadcast_notification(notification)
        
        return notification
    
    async def create_task_completion_notification(
        self,
        task_title: str,
        task_id: str,
        reward_info: Optional[Dict[str, Any]] = None,
        interest_vault_fact: Optional[str] = None
    ) -> EnhancedNotification:
        """
        Create a task completion notification with audio feedback.
        
        Args:
            task_title: Title of the completed task
            task_id: ID of the completed task
            reward_info: Optional reward information
            interest_vault_fact: Optional interest vault fact
            
        Returns:
            Created notification
        """
        # Determine audio type based on reward or task complexity
        audio_type = 'success'
        if reward_info and reward_info.get('type') == 'theme':
            audio_type = 'success'
        elif interest_vault_fact:
            audio_type = 'notification'
        
        # Create actions
        actions = [
            NotificationAction(
                type='view_task',
                label='View Task',
                action='view_task',
                icon='👁',
                data={'task_id': task_id}
            ),
            NotificationAction(
                type='share_achievement',
                label='Share Achievement',
                action='share_achievement',
                icon='📤'
            )
        ]
        
        # Build body with reward information
        body_parts = [f"Completed: {task_title}"]
        
        if reward_info:
            if reward_info.get('type') == 'theme':
                body_parts.append(f"Unlocked new theme: {reward_info.get('theme_name', 'Custom')}")
            elif reward_info.get('type') == 'audio':
                body_parts.append(f"Unlocked new audio: {reward_info.get('audio_name', 'Custom')}")
        
        if interest_vault_fact:
            body_parts.append(f"🎁 Interest Vault: {interest_vault_fact}")
        
        body = ' '.join(body_parts)
        
        return await self.create_notification(
            notification_type=NotificationType.COMPLETION_SUCCESS,
            title='🎉 Task Completed!',
            body=body,
            icon='🏆',
            actions=actions,
            audio_type=audio_type,
            priority='high',
            metadata={
                'task_id': task_id,
                'reward_info': reward_info,
                'interest_vault_fact': interest_vault_fact
            }
        )
    
    async def create_focus_mode_notification(
        self,
        is_entered: bool,
        duration_minutes: Optional[int] = None
    ) -> EnhancedNotification:
        """
        Create a focus mode notification.
        
        Args:
            is_entered: Whether focus mode is being entered or exited
            duration_minutes: Optional duration in minutes
            
        Returns:
            Created notification
        """
        if is_entered:
            title = '🎯 Focus Mode Activated'
            body = 'Focus mode is now active. Your task priority will be adjusted to help you concentrate.'
            if duration_minutes:
                body += f' Focus mode will last for {duration_minutes} minutes.'
            audio_type = 'notification'
        else:
            title = '☕ Focus Mode Deactivated'
            body = 'Focus mode has ended. Your task priority is back to normal.'
            audio_type = 'success'
        
        return await self.create_notification(
            notification_type=NotificationType.FOCUS_MODE_ENTERED if is_entered else NotificationType.FOCUS_MODE_EXITED,
            title=title,
            body=body,
            icon='🎯',
            audio_type=audio_type,
            priority='normal'
        )
    
    async def _broadcast_notification(self, notification: EnhancedNotification) -> None:
        """
        Broadcast notification via WebSocket.
        
        Args:
            notification: Notification to broadcast
        """
        # Convert notification to JSON for WebSocket transmission
        notification_data = {
            'id': notification.id,
            'type': notification.type.value,
            'title': notification.title,
            'body': notification.body,
            'icon': notification.icon,
            'actions': [
                {
                    'type': action.type,
                    'label': action.label,
                    'action': action.action,
                    'icon': action.icon,
                    'data': action.data
                }
                for action in (notification.actions or [])
            ],
            'audio_file': notification.audio_file,
            'priority': notification.priority,
            'timestamp': notification.timestamp,
            'metadata': notification.metadata
        }
        
        # Broadcast to all connected clients
        await ws_manager.publish(
            user_id=0,  # Broadcast to all users
            event='enhanced_notification',
            data=notification_data
        )
    
    def get_notification_history(self, limit: int = 50) -> List[EnhancedNotification]:
        """
        Get notification history.
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        return self._notification_history[-limit:]
    
    def get_active_notifications(self) -> List[EnhancedNotification]:
        """
        Get active notifications.
        
        Returns:
            List of active notifications
        """
        return list(self._active_notifications.values())


# Global service instance
enhanced_notification_service = EnhancedNotificationService()


def create_enhanced_notification(
    notification_type: NotificationType,
    title: str,
    body: str,
    icon: Optional[str] = None,
    actions: Optional[List[NotificationAction]] = None,
    audio_type: Optional[str] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None
) -> EnhancedNotification:
    """
    Convenience function to create an enhanced notification.
    
    Args:
        notification_type: Type of notification
        title: Notification title
        body: Notification body
        icon: Optional icon
        actions: Optional notification actions
        audio_type: Optional audio type for feedback
        priority: Notification priority
        metadata: Optional metadata
        
    Returns:
        Created notification
    """
    return enhanced_notification_service.create_notification(
        notification_type=notification_type,
        title=title,
        body=body,
        icon=icon,
        actions=actions,
        audio_type=audio_type,
        priority=priority,
        metadata=metadata
    )


def create_task_completion_notification(
    task_title: str,
    task_id: str,
    reward_info: Optional[Dict[str, Any]] = None,
    interest_vault_fact: Optional[str] = None
) -> EnhancedNotification:
    """
    Convenience function to create a task completion notification.
    
    Args:
        task_title: Title of the completed task
        task_id: ID of the completed task
        reward_info: Optional reward information
        interest_vault_fact: Optional interest vault fact
        
    Returns:
        Created notification
    """
    return enhanced_notification_service.create_task_completion_notification(
        task_title=task_title,
        task_id=task_id,
        reward_info=reward_info,
        interest_vault_fact=interest_vault_fact
    )


def create_focus_mode_notification(
    is_entered: bool,
    duration_minutes: Optional[int] = None
) -> EnhancedNotification:
    """
    Convenience function to create a focus mode notification.
    
    Args:
        is_entered: Whether focus mode is being entered or exited
        duration_minutes: Optional duration in minutes
        
    Returns:
        Created notification
    """
    return enhanced_notification_service.create_focus_mode_notification(
        is_entered=is_entered,
        duration_minutes=duration_minutes
    )
