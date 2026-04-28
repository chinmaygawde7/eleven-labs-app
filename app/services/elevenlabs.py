import requests
from app.config import Config

BASE_URL    = "https://api.elevenlabs.io/v1"
# Sarah — warm, calm, clear. Perfect for mental health context.
VOICE_ID    = "EXAVITQu4vr4xnSDxMaL"

LANGUAGE_CODES = {
    "English":  "en",
    "Hindi":    "hi",
    "Tamil":    "ta",
    "Telugu":   "te",
    "Marathi":  "hi",   # closest supported
    "Kannada":  "hi",
    "Bengali":  "hi",
    "Gujarati": "hi",
    "Punjabi":  "hi",
}


def synthesize_speech(text: str, language: str = "English") -> bytes:
    """
    Convert reflection text to calm spoken audio.
    Returns raw mp3 bytes.
    """
    lang_code = LANGUAGE_CODES.get(language, "en")

    response = requests.post(
        f"{BASE_URL}/text-to-speech/{VOICE_ID}",
        headers={
            "xi-api-key":   Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text":          text,
            "model_id":      "eleven_multilingual_v2",
            "language_code": lang_code,
            "voice_settings": {
                "stability":         0.65,
                "similarity_boost":  0.75,
                "style":             0.10,
                "use_speaker_boost": True,
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.content