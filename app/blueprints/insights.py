from flask import Blueprint, render_template, session
from app.blueprints.utils import login_required
from app.db.client import get_service_client
from collections import Counter
import datetime

insights_bp = Blueprint("insights", __name__)

MOOD_COLORS = {
    "happy":       "#4CAF50",
    "grateful":    "#8BC34A",
    "calm":        "#03A9F4",
    "anxious":     "#FF9800",
    "overwhelmed": "#FF5722",
    "sad":         "#5C6BC0",
    "angry":       "#F44336",
    "numb":        "#9E9E9E",
}


@insights_bp.route("/insights")
@login_required
def insights():
    db      = get_service_client()
    user_id = session["user_id"]

    # Last 30 days of entries
    thirty_days_ago = (
        datetime.datetime.utcnow() - datetime.timedelta(days=30)
    ).isoformat()

    entries = (
        db.table("journal_entries")
        .select("mood, created_at")
        .eq("user_id", user_id)
        .gte("created_at", thirty_days_ago)
        .order("created_at")
        .execute()
    ).data

    # Mood frequency count
    mood_counts = Counter(e["mood"] for e in entries)

    # Build chart data — last 30 days with mood per day
    days       = {}
    for entry in entries:
        day = entry["created_at"][:10]
        days[day] = entry["mood"]

    # Streak — consecutive days journaled
    streak      = 0
    today       = datetime.date.today()
    for i in range(30):
        day = (today - datetime.timedelta(days=i)).isoformat()
        if day in days:
            streak += 1
        else:
            break

    # Weekly summaries
    summaries = (
        db.table("weekly_summaries")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(4)
        .execute()
    ).data

    for s in summaries:
        if s.get("audio_path"):
            try:
                signed = db.storage.from_("audio").create_signed_url(
                    s["audio_path"], 3600
                )
                s["audio_url"] = signed["signedURL"]
            except Exception:
                s["audio_url"] = None

    return render_template(
        "journal/insights.html",
        entries=entries,
        mood_counts=dict(mood_counts),
        mood_colors=MOOD_COLORS,
        days=days,
        streak=streak,
        total=len(entries),
        summaries=summaries,
        today=datetime.date.today(),
        timedelta=datetime.timedelta

    )