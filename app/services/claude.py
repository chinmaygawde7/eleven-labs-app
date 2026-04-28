import anthropic
from app.config import Config

_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

SUPPORTED_LANGUAGES = {
    "English":    "English",
    "Hindi":      "Hindi (हिन्दी)",
    "Marathi":    "Marathi (मराठी)",
    "Tamil":      "Tamil (தமிழ்)",
    "Telugu":     "Telugu (తెలుగు)",
    "Kannada":    "Kannada (ಕನ್ನಡ)",
    "Malayalam":  "Malayalam (മലയാളം)",
    "Bengali":    "Bengali (বাংলা)",
    "Gujarati":   "Gujarati (ગુજરાતી)",
    "Punjabi":    "Punjabi (ਪੰਜਾਬੀ)",
    "Odia":       "Odia (ଓଡ଼ିଆ)",
    "Urdu":       "Urdu (اردو)",
    "Sanskrit":   "Sanskrit (संस्कृतम्)",
}

# Maps our language to the closest ElevenLabs supported language
# ElevenLabs multilingual v2 supports these natively
ELEVENLABS_LANGUAGE_MAP = {
    "English":   "English",
    "Hindi":     "Hindi",
    "Tamil":     "Tamil",
    "Telugu":    "Telugu",
    "Marathi":   "Hindi",    # closest supported
    "Kannada":   "Hindi",    # closest supported
    "Malayalam": "Tamil",    # closest supported
    "Bengali":   "Hindi",    # closest supported
    "Gujarati":  "Hindi",    # closest supported
    "Punjabi":   "Hindi",    # closest supported
    "Odia":      "Hindi",    # closest supported
    "Urdu":      "Hindi",    # closest supported
    "Sanskrit":  "Hindi",    # closest supported
}


def generate_message(
    loved_one_name:    str,
    relationship:      str,
    personality_notes: str,
    occasion_label:    str,
    recipient_name:    str,
    message_language:  str = "English",
) -> str:
    """
    Ask Claude to write a spoken message in the loved one's voice.
    message_language controls what language the script is written in.
    Returns 80–120 words of plain text ready for ElevenLabs TTS.
    """
    system = f"""You write short personal voice messages that sound like they come
from a specific real person speaking to someone they love deeply.
The message is converted to audio using their cloned voice — write for the ear.

Rules:
- First person as {loved_one_name}
- 80 to 120 words only
- Write entirely in {message_language} — do not mix languages unless the personality
  notes indicate the person naturally code-switched (e.g. Hindi + English)
- Warm, personal, and natural — no clichés like "gone too soon" or "watching over you"
- Reference the occasion without being heavy-handed
- End with a tender sign-off that fits the relationship and language
- Output ONLY the message text — no stage directions, no quotes, no preamble"""

    user = f"""Write a voice message from {loved_one_name} ({relationship})
to {recipient_name} for: {occasion_label}.

How {loved_one_name} spoke and their personality:
{personality_notes or "Warm, loving, always encouraging."}

Write the message in {message_language}.
This plays as real audio in their cloned voice. Make it feel like they are truly there."""

    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()