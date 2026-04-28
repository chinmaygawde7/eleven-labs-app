import uuid
import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, jsonify, flash
)
from app.blueprints.utils import login_required
from app.db.client import get_service_client
from app.services.claude import reflect_on_entry, MOODS, LANGUAGES
from app.services.elevenlabs import synthesize_speech

journal_bp = Blueprint("journal", __name__)


@journal_bp.route("/")
@journal_bp.route("/write")
@login_required
def write():
    return render_template(
        "journal/write.html",
        moods=MOODS,
        languages=LANGUAGES,
    )


@journal_bp.route("/entry", methods=["POST"])
@login_required
def submit_entry():
    """
    Receives journal entry from the form.
    1. Claude writes a reflection
    2. ElevenLabs synthesizes it
    3. Audio uploaded to Supabase Storage
    4. Entry saved to DB
    5. Returns JSON with reflection text + audio URL
    """
    db      = get_service_client()
    user_id = session["user_id"]

    entry_text = request.json.get("entry_text", "").strip()
    mood       = request.json.get("mood", "").strip()
    language   = request.json.get("language", "English").strip()

    if not entry_text:
        return jsonify({"error": "Please write something before submitting."}), 400

    if not mood:
        return jsonify({"error": "Please select a mood."}), 400

    if len(entry_text) < 10:
        return jsonify({"error": "Entry is too short. Write a little more."}), 400

    try:
        # 1. Claude reflects
        reflection = reflect_on_entry(entry_text, mood, language)

        # 2. ElevenLabs synthesizes
        audio_bytes = synthesize_speech(reflection, language)

        # 3. Upload audio
        entry_id  = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path      = f"journal/{user_id}/{timestamp}_{entry_id}.mp3"

        db.storage.from_("audio").upload(
            path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )

        # Signed URL valid 24 hours for immediate playback
        signed    = db.storage.from_("audio").create_signed_url(path, 86400)
        audio_url = signed["signedURL"]

        # 4. Save entry to DB
        db.table("journal_entries").insert({
            "id":         entry_id,
            "user_id":    user_id,
            "entry_text": entry_text,
            "mood":       mood,
            "reflection": reflection,
            "audio_path": path,
            "language":   language,
        }).execute()

        return jsonify({
            "success":    True,
            "reflection": reflection,
            "audio_url":  audio_url,
            "mood":       mood,
        })

    except Exception as e:
        print("JOURNAL ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


@journal_bp.route("/history")
@login_required
def history():
    db      = get_service_client()
    user_id = session["user_id"]

    entries = (
        db.table("journal_entries")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    ).data

    # Generate fresh signed URLs for each entry's audio
    for entry in entries:
        if entry.get("audio_path"):
            try:
                signed = db.storage.from_("audio").create_signed_url(
                    entry["audio_path"], 3600
                )
                entry["audio_url"] = signed["signedURL"]
            except Exception:
                entry["audio_url"] = None

    return render_template("journal/history.html", entries=entries)


@journal_bp.route("/entry/<entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: str):
    db      = get_service_client()
    user_id = session["user_id"]

    result = (
        db.table("journal_entries")
        .select("audio_path")
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    entry = result.data
    if entry and entry.get("audio_path"):
        try:
            db.storage.from_("audio").remove([entry["audio_path"]])
        except Exception:
            pass

    db.table("journal_entries").delete()\
        .eq("id", entry_id)\
        .eq("user_id", user_id)\
        .execute()

    flash("Entry deleted.", "success")
    return redirect(url_for("journal.history"))