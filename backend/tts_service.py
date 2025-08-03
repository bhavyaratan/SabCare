import os
import tempfile
import requests
from typing import Optional, Dict, Any
import json
from voice_config import voice_config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.config = voice_config
        self.call_status = {}  # Track call status and delivery confirmations
        
    def text_to_speech_azure(self, text: str, filename: str = None, language: str = "en-US", voice_name: str = None) -> str:
        """Convert text to speech using Azure Speech Services with enhanced language support"""
        try:
            azure_key = self.config.get_api_key("azure")
            if not azure_key:
                logger.warning("Azure Speech key not found, falling back to Google TTS")
                return self.text_to_speech_google(text, filename, language)
            
            import azure.cognitiveservices.speech as speechsdk
            
            # Get voice settings with language support
            settings = self.config.get_voice_settings("azure")
            
            # Configure speech config with language
            speech_config = speechsdk.SpeechConfig(
                subscription=azure_key, 
                region=self.config.api_keys["azure_region"]
            )
            
            # Set language and voice
            speech_config.speech_synthesis_language = language
            if voice_name:
                speech_config.speech_synthesis_voice_name = voice_name
            else:
                # Default voice for language
                voice_map = {
                    "en-US": "en-US-JennyNeural",
                    "es-ES": "es-ES-ElviraNeural", 
                    "fr-FR": "fr-FR-DeniseNeural",
                    "hi-IN": "hi-IN-SwaraNeural",
                    "zh-CN": "zh-CN-XiaoxiaoNeural"
                }
                speech_config.speech_synthesis_voice_name = voice_map.get(language, "en-US-JennyNeural")
            
            # Enhanced voice settings
            speech_config.speech_synthesis_speaking_rate = settings.get("speaking_rate", 1.0)
            speech_config.speech_synthesis_pitch = settings.get("pitch", 0)
            speech_config.speech_synthesis_volume = settings.get("volume", 1.0)
            
            # Generate filename if not provided
            if not filename:
                import uuid
                filename = f"ivr_message_{uuid.uuid4().hex[:8]}.wav"
            
            # Save to temporary file
            file_path = os.path.join(self.temp_dir, filename)
            
            # Create audio config
            audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)
            
            # Create synthesizer
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Synthesize speech
            result = speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"Azure TTS generated: {file_path} (Language: {language})")
                return file_path
            else:
                logger.error(f"Azure TTS failed: {result.reason}")
                return self.text_to_speech_google(text, filename, language)
                
        except Exception as e:
            logger.error(f"Azure TTS Error: {e}")
            return self.text_to_speech_google(text, filename, language)
    
    def text_to_speech_elevenlabs(self, text: str, filename: str = None, voice_id: str = None) -> str:
        """Convert text to speech using ElevenLabs with enhanced voice options"""
        try:
            elevenlabs_key = self.config.get_api_key("elevenlabs")
            if not elevenlabs_key:
                logger.warning("ElevenLabs API key not found, falling back to Google TTS")
                return self.text_to_speech_google(text, filename)
            
            # Get voice settings
            settings = self.config.get_voice_settings("elevenlabs")
            
            # Use provided voice_id or default
            if not voice_id:
                voice_id = settings.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice
            
            # Generate filename if not provided
            if not filename:
                import uuid
                filename = f"ivr_message_{uuid.uuid4().hex[:8]}.mp3"
            
            # Save to temporary file
            file_path = os.path.join(self.temp_dir, filename)
            
            # ElevenLabs API call with enhanced settings
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_key
            }
            
            data = {
                "text": text,
                "model_id": settings.get("model_id", "eleven_monolingual_v1"),
                "voice_settings": {
                    "stability": settings.get("stability", 0.5),
                    "similarity_boost": settings.get("similarity_boost", 0.5),
                    "style": settings.get("style", 0.0),
                    "use_speaker_boost": settings.get("use_speaker_boost", True)
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"ElevenLabs TTS generated: {file_path}")
                return file_path
            else:
                logger.error(f"ElevenLabs TTS failed: {response.status_code}")
                return self.text_to_speech_google(text, filename)
                
        except Exception as e:
            logger.error(f"ElevenLabs TTS Error: {e}")
            return self.text_to_speech_google(text, filename)
    
    def text_to_speech_google(self, text: str, filename: str = None, language: str = "en") -> str:
        """Convert text to speech using Google TTS with enhanced language support"""
        try:
            from gtts import gTTS
            
            # Get voice settings
            settings = self.config.get_voice_settings("google")
            
            # Language mapping for better voice quality
            language_map = {
                "en": "en",
                "es": "es", 
                "fr": "fr",
                "hi": "hi",
                "zh": "zh"
            }
            
            tts_language = language_map.get(language, "en")
            
            # Create TTS object with enhanced settings
            tts = gTTS(
                text=text, 
                lang=tts_language, 
                slow=settings.get("slow", False),
                tld=settings.get("tld", "com")
            )
            
            # Generate filename if not provided
            if not filename:
                import uuid
                filename = f"ivr_message_{uuid.uuid4().hex[:8]}.mp3"
            
            # Save to temporary file
            file_path = os.path.join(self.temp_dir, filename)
            tts.save(file_path)
            
            logger.info(f"Google TTS generated: {file_path} (Language: {language})")
            return file_path
            
        except Exception as e:
            logger.error(f"Google TTS Error: {e}")
            return None
    
    def improve_text_for_tts(self, text: str, language: str = "en") -> str:
        """Improve text formatting for better TTS quality with language-specific enhancements"""
        improvements = self.config.text_improvements
        
        if not improvements.get("add_pauses", True):
            return text
        
        improved_text = text
        
        # Language-specific improvements
        if language == "en":
            # Add pauses for better speech flow
            for char in improvements.get("pause_characters", ['.', '!', '?', ';']):
                improved_text = improved_text.replace(char, improvements.get("pause_replacement", '... '))
            
            # Add emphasis to important medical terms
            medical_terms = improvements.get("medical_terms", [
                'medication', 'vitamins', 'doctor', 'healthcare', 'pregnancy',
                'baby', 'movements', 'contact', 'immediately', 'important',
                'prescribed', 'symptoms', 'emergency', 'appointment'
            ])
            
            for term in medical_terms:
                if term in improved_text.lower():
                    # Add slight pause before important terms
                    improved_text = improved_text.replace(term, f'... {term}')
        
        elif language == "es":
            # Spanish-specific improvements
            spanish_terms = ['medicamento', 'vitaminas', 'doctor', 'embarazo', 'bebé']
            for term in spanish_terms:
                if term in improved_text.lower():
                    improved_text = improved_text.replace(term, f'... {term}')
        
        elif language == "hi":
            # Hindi-specific improvements
            hindi_terms = ['दवा', 'विटामिन', 'डॉक्टर', 'गर्भावस्था', 'बच्चा']
            for term in hindi_terms:
                if term in improved_text.lower():
                    improved_text = improved_text.replace(term, f'... {term}')
        
        return improved_text
    
    def text_to_speech(self, text: str, filename: str = None, language: str = "en", voice_id: str = None) -> str:
        """Convert text to speech using the best available provider with language support"""
        # Improve text formatting for better TTS quality
        improved_text = self.improve_text_for_tts(text, language)
        
        # Get the best available provider
        provider = self.config.get_best_provider()
        
        if provider == "azure":
            return self.text_to_speech_azure(improved_text, filename, language)
        elif provider == "elevenlabs":
            return self.text_to_speech_elevenlabs(improved_text, filename, voice_id)
        else:
            return self.text_to_speech_google(improved_text, filename, language)
    
    def track_call_status(self, call_id: str, status: str, details: Dict[str, Any] = None):
        """Track call status and delivery confirmations"""
        self.call_status[call_id] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        logger.info(f"Call {call_id} status: {status}")
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get call status and delivery confirmation"""
        return self.call_status.get(call_id, {"status": "unknown"})
    
    def cleanup_audio_file(self, file_path: str):
        """Clean up temporary audio file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up audio file: {file_path}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Global instance
tts_service = TTSService() 