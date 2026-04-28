from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def send_weekly_summaries():
    """
    Runs every Sunday at 08:00 UTC.
    For each user who journaled in the past 7 days:
    - fetch their entries
    - Claude writes a weekly summary
    - ElevenLabs narrates it
    - Resend emails the audio link
    """
    from app.db.client import get_service_client
    from app.services.claude import generate_weekly_summary
    from app.services.elevenlabs import synthesize_speech
    from app.services.email import send_weekly_email

    db        = get_service_client()
    week_ago  = (datetime.utcnow() - timedelta(days=7)).isoformat()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Get all profiles
    profiles = db.table("profiles").select("*").execute().data

    for profile in profiles:
        try:
            user_id = profile["id"]

            # Fetch this week's entries
            entries = (
                db.table("journal_entries")
                .select("*")
                .eq("user_id", user_id)
                .gte("created_at", week_ago)
                .order("created_at")
                .execute()
            ).data

            if not entries:
                continue

            language = entries[-1].get("language", "English")

            # Claude writes the summary
            summary_text, dominant_mood = generate_weekly_summary(entries, language)

            # ElevenLabs narrates it
            audio_bytes = synthesize_speech(summary_text, language)

            # Upload to storage
            path = f"weekly/{user_id}/{today_str}.mp3"
            db.storage.from_("audio").upload(
                path, audio_bytes,
                {"content-type": "audio/mpeg", "upsert": "true"},
            )

            signed    = db.storage.from_("audio").create_signed_url(path, 604800)
            audio_url = signed["signedURL"]

            # Save to DB
            db.table("weekly_summaries").insert({
                "user_id":       user_id,
                "week_start":    today_str,
                "summary_text":  summary_text,
                "audio_path":    path,
                "dominant_mood": dominant_mood,
            }).execute()

            # Email
            send_weekly_email(
                to_email=profile["email"],
                recipient_name=profile.get("full_name", ""),
                audio_url=audio_url,
                summary_text=summary_text,
            )

            print(f"[scheduler] Weekly summary sent → {profile['email']}")

        except Exception as e:
            print(f"[scheduler] Failed for {profile.get('email')}: {e}")
            continue


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_weekly_summaries,
        trigger=CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_summary",
        replace_existing=True,
    )
    scheduler.start()
    print("[scheduler] Started — weekly summaries every Sunday 08:00 UTC")