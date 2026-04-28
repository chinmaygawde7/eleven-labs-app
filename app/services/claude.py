import anthropic
from app.config import Config

_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

MOODS = ["happy", "anxious", "sad", "grateful", "angry", "numb", "overwhelmed", "calm"]

LANGUAGES = {
    "English":   "English",
    "Hindi":     "Hindi (हिन्दी)",
    "Marathi":   "Marathi (मराठी)",
    "Tamil":     "Tamil (தமிழ்)",
    "Telugu":    "Telugu (తెలుగు)",
    "Kannada":   "Kannada (ಕನ್ನಡ)",
    "Bengali":   "Bengali (বাংলা)",
    "Gujarati":  "Gujarati (ગુજરાતી)",
    "Punjabi":   "Punjabi (ਪੰਜਾਬੀ)",
}


def reflect_on_entry(entry_text: str, mood: str, language: str = "English") -> str:
    """
    Read the user's journal entry and write a warm, human reflection.
    Not therapy. Not advice. Just presence and acknowledgement.
    Returns 80-100 words spoken naturally.
    """
    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=f"""You are a warm, calm presence — like a trusted friend who truly listens.
Someone has shared their journal entry with you. Your job is to reflect it back
with empathy, making them feel heard. You are NOT a therapist. You do NOT give advice.
You do NOT diagnose or suggest solutions.

Rules:
- Write in second person (you, your)
- 80 to 100 words only — this will be spoken aloud
- Acknowledge the specific feelings they described, not generic ones
- Warm and grounded — never clinical, never preachy
- End with one gentle, open sentence that invites them to keep going
- Write entirely in {language}
- Output ONLY the reflection — no preamble, no labels""",
        messages=[{
            "role": "user",
            "content": (
                f"Mood: {mood}\n\n"
                f"Journal entry:\n{entry_text}\n\n"
                f"Write a warm reflection in {language}."
            ),
        }],
    )
    return response.content[0].text.strip()


def generate_weekly_summary(
    entries: list[dict],
    language: str = "English",
) -> tuple[str, str]:
    """
    Given a week's journal entries, write a summary and identify the dominant mood.
    Returns (summary_text, dominant_mood).
    """
    if not entries:
        return "You didn't journal this week — and that's okay. This week is a fresh start.", "calm"

    entries_text = "\n\n".join([
        f"Day {i+1} ({e['mood']}):\n{e['entry_text']}"
        for i, e in enumerate(entries)
    ])

    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=f"""You write warm, honest weekly reflections for a journaling app.
You have access to a person's journal entries from the past week.
Write a spoken summary they will hear as an audio message on Sunday morning.

Rules:
- 120 to 150 words — spoken naturally, no bullet points
- Acknowledge the emotional arc of the week honestly
- Note specific things they mentioned — make it personal not generic
- End with one line of gentle encouragement for the week ahead
- Write entirely in {language}
- Return JSON with exactly two keys: "summary" and "dominant_mood"
- dominant_mood must be one of: happy, anxious, sad, grateful, angry, numb, overwhelmed, calm
- No markdown, no preamble""",
        messages=[{
            "role": "user",
            "content": (
                f"Here are this week's journal entries:\n\n{entries_text}\n\n"
                f"Write the weekly summary in {language}."
            ),
        }],
    )

    import json
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    data = json.loads(text)
    return data["summary"], data["dominant_mood"]