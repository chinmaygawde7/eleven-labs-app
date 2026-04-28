from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def deliver_todays_messages():
    from app.db.client import get_service_client
    from app.services.elevenlabs import synthesize_speech
    from app.services.claude import generate_message
    from app.services.email import send_audio_email

    db    = get_service_client()
    today = datetime.utcnow()

    rows = (
        db.table("memory_dates")
        .select("*, loved_ones(*), profiles!memory_dates_user_id_fkey(*)")
        .eq("month",  today.month)
        .eq("day",    today.day)
        .eq("active", True)
        .execute()
    ).data

    for row in rows:
        try:
            loved_one        = row["loved_ones"]
            profile          = row["profiles"]
            message_language = loved_one.get("message_language", "English")

            if not loved_one.get("voice_id"):
                continue

            script = generate_message(
                loved_one_name=loved_one["name"],
                relationship=loved_one["relationship"],
                personality_notes=loved_one.get("personality_notes", ""),
                occasion_label=row["label"],
                recipient_name=profile.get("full_name", "my dear"),
                message_language=message_language,
            )

            audio_bytes = synthesize_speech(
                voice_id=loved_one["voice_id"],
                text=script,
                language=message_language,
            )

            path = (
                f"generated-audio/{row['user_id']}/"
                f"{row['id']}/{today.strftime('%Y-%m-%d')}.mp3"
            )
            db.storage.from_("audio").upload(
                path, audio_bytes,
                {"content-type": "audio/mpeg", "upsert": "true"},
            )

            signed    = db.storage.from_("audio").create_signed_url(path, 604800)
            audio_url = signed["signedURL"]

            send_audio_email(
                to_email=profile["email"],
                recipient_name=profile.get("full_name", ""),
                loved_one_name=loved_one["name"],
                occasion_label=row["label"],
                audio_url=audio_url,
            )

            db.table("delivered_messages").insert({
                "user_id":        row["user_id"],
                "loved_one_id":   row["loved_one_id"],
                "memory_date_id": row["id"],
                "script":         script,
                "audio_path":     path,
            }).execute()

            print(f"[scheduler] Delivered: {loved_one['name']} → {profile['email']}")

        except Exception as e:
            print(f"[scheduler] Failed for row {row['id']}: {e}")
            continue


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        deliver_todays_messages,
        trigger=CronTrigger(hour=7, minute=0),
        id="deliver_messages",
        replace_existing=True,
    )
    scheduler.start()
    print("[scheduler] Started — delivers messages daily at 07:00 UTC")