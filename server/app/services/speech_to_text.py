"""
Speech-to-text service for voice task ingestion.

This service converts audio data to text using OpenAI Whisper.
"""

import base64
import logging
import io
import os
from typing import Optional
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Convert audio data to text for task ingestion using OpenAI Whisper."""
    
    def __init__(self):
        self.client = None
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            logger.warning("OPENAI_API_KEY not found in environment. Voice transcription will fail.")
    
    def audio_to_text(self, audio_data: str, source_type: str = 'voice') -> str:
        """
        Convert base64 audio data to text using OpenAI Whisper.
        
        Args:
            audio_data: Base64 encoded audio data
            source_type: Type of source (voice, etc.)
            
        Returns:
            Transcribed text
        """
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            if not self.client:
                raise ValueError("OpenAI client not configured (Missing OPENAI_API_KEY in .env)")
            
            # Create a file-like object with a name required by OpenAI
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.webm"
            
            logger.info("Sending audio to OpenAI Whisper API...")
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
            transcribed_text = transcription.text
            logger.info("Successfully transcribed audio: %s", transcribed_text)
            
            return transcribed_text
            
        except Exception as e:
            logger.error("Error converting audio to text: %s", e)
            raise e


# Global service instance
speech_to_text_service = SpeechToTextService()


def convert_audio_to_text(audio_data: str, source_type: str = 'voice') -> str:
    """
    Convenience function to convert audio data to text.
    
    Args:
        audio_data: Base64 encoded audio data
        source_type: Type of source (voice, etc.)
        
    Returns:
        Transcribed text
    """
    return speech_to_text_service.audio_to_text(audio_data, source_type)
