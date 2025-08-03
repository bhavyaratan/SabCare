import os
from typing import Dict, Any

class VoiceConfig:
    def __init__(self):
        # Default voice provider (options: "google", "azure", "elevenlabs")
        self.default_provider = "google"
        
        # Voice settings for each provider
        self.voice_settings = {
            "google": {
                "lang": "en",
                "slow": False,
                "tld": "com"
            },
            "azure": {
                "voice_name": "en-US-JennyNeural",  # Natural-sounding female voice
                "speaking_rate": 1.0,
                "pitch": 0,
                "volume": 1.0
            },
            "elevenlabs": {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
                "model_id": "eleven_monolingual_v1",
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # API Keys (set via environment variables)
        self.api_keys = {
            "azure": os.getenv("AZURE_SPEECH_KEY"),
            "azure_region": os.getenv("AZURE_SPEECH_REGION", "eastus"),
            "elevenlabs": os.getenv("ELEVENLABS_API_KEY")
        }
        
        # Text improvement settings
        self.text_improvements = {
            "add_pauses": True,
            "medical_terms": [
                'medication', 'vitamins', 'doctor', 'healthcare', 'pregnancy',
                'baby', 'movements', 'contact', 'immediately', 'important',
                'prescribed', 'symptoms', 'emergency', 'appointment'
            ],
            "pause_characters": ['.', '!', '?', ';'],
            "pause_replacement": '... '
        }
    
    def get_available_providers(self) -> list:
        """Get list of available TTS providers based on API keys"""
        providers = ["google"]  # Google TTS is always available
        
        if self.api_keys["azure"]:
            providers.append("azure")
        
        if self.api_keys["elevenlabs"]:
            providers.append("elevenlabs")
        
        return providers
    
    def get_best_provider(self) -> str:
        """Get the best available TTS provider"""
        available = self.get_available_providers()
        
        # Priority order: ElevenLabs > Azure > Google
        if "elevenlabs" in available:
            return "elevenlabs"
        elif "azure" in available:
            return "azure"
        else:
            return "google"
    
    def get_voice_settings(self, provider: str) -> Dict[str, Any]:
        """Get voice settings for a specific provider"""
        return self.voice_settings.get(provider, {})
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for a specific provider"""
        return self.api_keys.get(provider)

# Global instance
voice_config = VoiceConfig() 