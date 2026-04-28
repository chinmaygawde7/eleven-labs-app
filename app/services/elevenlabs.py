import requests
from app.config import Config

BASE_URL = "https://api.elevenlabs.io/v1"


def _headers(json=False) -> dict:
    h = {"xi-api-key": Config.ELEVENLABS_API_KEY}
    if json:
        h["Content-Type"] = "application/json"
    return h


def clone_voice(audio_bytes: bytes, name: str, description: str) -> str:
    """
    Send audio to ElevenLabs instant voice clone.
    Returns the voice_id — save this to the DB.
    """
    response = requests.post(
        f"{BASE_URL}/voices/add",
        headers={"xi-api-key": Config.ELEVENLABS_API_KEY},  # NO Content-Type here
        files=[
            ("files", ("sample.mp3", audio_bytes, "audio/mpeg")),
        ],
        data={
            "name":                    name,
            "description":             description,
            "remove_background_noise": "true",
        },
        timeout=60,
    )

    # Print full error detail before raising
    if not response.ok:
        print("ELEVENLABS ERROR:", response.status_code, response.text)
        response.raise_for_status()

    return response.json()["voice_id"]


def synthesize_speech(voice_id: str, text: str, language: str = "English") -> bytes:
    """
    Convert a text script into speech using the cloned voice.
    Language hint helps ElevenLabs pick correct phonemes.
    Returns raw mp3 bytes.
    """
    from app.services.claude import ELEVENLABS_LANGUAGE_MAP
    el_language = ELEVENLABS_LANGUAGE_MAP.get(language, "English")

    response = requests.post(
        f"{BASE_URL}/text-to-speech/{voice_id}",
        headers=_headers(json=True),
        json={
            "text":      text,
            "model_id":  "eleven_multilingual_v2",
            "language_code": _to_language_code(el_language),
            "voice_settings": {
                "stability":         0.45,
                "similarity_boost":  0.85,
                "style":             0.20,
                "use_speaker_boost": True,
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def _to_language_code(language: str) -> str:
    """Maps language name to BCP-47 code for ElevenLabs."""
    codes = {
        "English":    "en",
        "Hindi":      "hi",
        "Tamil":      "ta",
        "Telugu":     "te",
        "Portuguese": "pt",
        "Spanish":    "es",
        "French":     "fr",
        "German":     "de",
        "Japanese":   "ja",
        "Korean":     "ko",
        "Chinese":    "zh",
        "Arabic":     "ar",
        "Italian":    "it",
    }
    return codes.get(language, "en")


def delete_voice(voice_id: str) -> None:
    """Remove a cloned voice from ElevenLabs."""
    requests.delete(
        f"{BASE_URL}/voices/{voice_id}",
        headers=_headers(),
        timeout=30,
    )