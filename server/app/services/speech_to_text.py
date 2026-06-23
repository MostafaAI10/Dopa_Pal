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

    def audio_bytes_to_text(self, audio_bytes: bytes) -> str:
        """
        Accepts raw file binary bytes (WebM/Ogg), converts it via ffmpeg stream buffers,
        and transcribes it directly using the Google Web Speech API.
        """
        try:
            if not audio_bytes:
                logger.error("❌ Received empty audio bytes")
                raise ValueError("Uploaded file is empty")

            logger.info(f"📥 [STREAMING AUDIO] Received {len(audio_bytes)} bytes")

            # 1. Initialize input buffer directly from raw stream memory
            audio_file = io.BytesIO(audio_bytes)
            
            # 2. Parse inside pydub 
            audio_segment = AudioSegment.from_file(audio_file)
            
            logger.info(f"📊 [STREAMING AUDIO STATS] Duration: {audio_segment.duration_seconds:.2f}s")
            logger.info(f"🔊 [STREAMING AUDIO STATS] Max Decibel Level: {audio_segment.max_dBFS:.2f} dBFS")

            if audio_segment.duration_seconds < 0.3:
                raise ValueError("Recording too short (%.1fs). Please speak longer." % audio_segment.duration_seconds)
            
            if audio_segment.max_dBFS < -75:
                logger.warning("⚠️ Received stream file consists entirely of digital silence.")

            # 3. Stream convert straight into intermediate PCM WAV block
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            
            # 4. Transcribe
            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)
                
            transcribed_text = self.recognizer.recognize_google(audio, language='en-US')
            logger.info(f"🗣️ Transcribed Result: '{transcribed_text}'")
            return transcribed_text
            
        except sr.UnknownValueError:
            logger.error("Speech Recognition layer could not decode speech elements.")
            raise ValueError("Speech not understood. Please speak more clearly or record longer.")
        except sr.RequestError as e:
            logger.error(f"Google Web Speech upstream connection drop: {e}")
            raise ValueError("Upstream speech processing service temporarily unavailable.")
        except Exception as e:
            logger.error(f"Error handling system audio stream parsing down line: {e}")
            raise ValueError(f"Media translation engine failure: {str(e)}")

    def audio_to_text(self, audio_data: str, source_type: str = "voice") -> str:
        """
        Converts base64 encoded audio to text using SpeechRecognition (Google).
        """
        try:
            # 1. Inspect raw payload format before processing
            if not audio_data:
                logger.error("❌ RAW DATA IS COMPLETELY EMPTY")
                raise ValueError("Received empty audio data")
                
            logger.info(f"📋 [RAW INCOMING] Length: {len(audio_data)} characters")
            logger.info(f"📋 [RAW INCOMING] Start snippet: '{audio_data[:60]}'")
            logger.info(f"📋 [RAW INCOMING] End snippet: '{audio_data[-60:]}'")

            # 2. Handle data URI stripping safely if sent by browser APIs
            if "," in audio_data:
                logger.info("Stripping data URI header from incoming base64 payload.")
                audio_data = audio_data.split(",")[1]

            # 3. Decode base64 audio data with protective logging
            try:
                audio_bytes = base64.b64decode(audio_data)
                logger.info(f"🔓 [DECODED] Success! Output byte size: {len(audio_bytes)} bytes")
            except Exception as b64_err:
                logger.error(f"❌ BASE64 DECODING FAILED: {str(b64_err)}")
                raise ValueError("Payload is not valid base64 encoding")
            
            if not audio_bytes:
                raise ValueError("Received empty audio data or corrupted base64 string")
            
            logger.info("Converting audio to WAV format via ffmpeg...")
            # Load WebM/Ogg audio from memory
            audio_file = io.BytesIO(audio_bytes)
            audio_segment = AudioSegment.from_file(audio_file)
            
            # 4. Extract track diagnostics
            logger.info(f"📊 [AUDIO STATS] Duration: {audio_segment.duration_seconds:.2f} seconds")
            logger.info(f"🔊 [AUDIO STATS] Max Decibel Level (dBFS): {audio_segment.max_dBFS:.2f}")

            if audio_segment.duration_seconds < 0.3:
                raise ValueError("Recording too short (%.1fs). Please speak longer." % audio_segment.duration_seconds)
            
            if audio_segment.max_dBFS < -80:
                logger.warning("⚠️ [AUDIO STATS WARNING] The received audio file contains nothing but silence!")
            
            # Export as WAV to a new BytesIO buffer
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")  # type: ignore
            wav_io.seek(0)
            
            logger.info("Sending audio to SpeechRecognition (Google Web API)...")
            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)
            
            # Using Google Web Speech API tuned for English tasks
            transcribed_text = self.recognizer.recognize_google(audio, language='en-US')  # type: ignore
            
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