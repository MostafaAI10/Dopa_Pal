"""
Speech-to-text service for voice task ingestion.

This service converts audio data to text using SpeechRecognition and Google Web Speech API.
"""

import base64
import io
import logging
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class SpeechToTextService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def audio_to_text(self, audio_data: str, source_type: str = "voice") -> str:
        """
        Converts base64 encoded audio to text using SpeechRecognition (Google).
        """
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            if not audio_bytes:
                raise ValueError("Received empty audio data")
            
            logger.info("Converting audio to WAV format...")
            # Load WebM/Ogg audio from memory
            audio_file = io.BytesIO(audio_bytes)
            audio_segment = AudioSegment.from_file(audio_file)
            
            # Export as WAV to a new BytesIO buffer
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")  # type: ignore
            wav_io.seek(0)
            
            logger.info("Sending audio to SpeechRecognition (Google Web API)...")
            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)
            
            # Using Google Web Speech API (free, no key required)
            transcribed_text = self.recognizer.recognize_google(audio, language='ar-SA')  # type: ignore
            
            logger.info("Successfully transcribed audio: %s", transcribed_text)
            
            return transcribed_text
            
        except ValueError:
            raise
        except sr.UnknownValueError:
            logger.error("Google Speech Recognition could not understand audio")
            raise ValueError("Voice transcription failed: Could not understand audio")
        except sr.RequestError as e:
            logger.error("Could not request results from Google Speech Recognition service; {0}".format(e))
            raise ValueError(f"Voice transcription failed: API error {e}")
        except Exception as e:
            logger.error("Error converting audio to text: %s", e)
            raise ValueError(f"Voice transcription failed: {str(e)}")


# Global service instance
speech_to_text_service = SpeechToTextService()


def convert_audio_to_text(audio_data: str, source_type: str = "voice") -> str:
    """
    Module-level function to convert audio to text.
    Uses the global SpeechToTextService instance.
    
    Args:
        audio_data: Base64 encoded audio data
        source_type: Type of source (voice, etc.)
        
    Returns:
        Transcribed text
    """
    return speech_to_text_service.audio_to_text(audio_data, source_type)
