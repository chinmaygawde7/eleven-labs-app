import uuid
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, jsonify, flash
)
from app.blueprints.utils import login_required
from app.db.client import get_service_client
from app.services.elevenlabs import clone_voice, delete_voice
from app.services.claude import SUPPORTED_LANGUAGES

voice_bp = Blueprint("voice", __name__, url_prefix="/voice")

ALLOWED   = {"mp3", "wav", "m4a", "ogg", "webm"}
MAX_BYTES = 25 * 1024 * 1024


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@voice_bp.route("/onboarding")
@login_required
def onboarding():
    return render_template(
        "onboarding/index.html",
        languages=SUPPORTED_LANGUAGES,
    )


@voice_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    name              = request.form.get("name", "").strip()
    relationship      = request.form.get("relationship", "").strip()
    personality_notes = request.form.get("personality_notes", "").strip()
    audio_language    = request.form.get("audio_language", "English").strip()
    message_language  = request.form.get("message_language", "English").strip()
    audio_file        = request.files.get("audio")

    if not name or not relationship:
        return jsonify({"error": "Name and relationship are required."}), 400
    if not audio_file or audio_file.filename == "":
        return jsonify({"error": "Please select an audio file."}), 400
    if not _allowed(audio_file.filename):
        return jsonify({"error": "Allowed formats: mp3, wav, m4a, ogg, webm."}), 400

    audio_bytes = audio_file.read()
    if len(audio_bytes) > MAX_BYTES:
        return jsonify({"error": "File too large. Maximum is 25 MB."}), 400

    db      = get_service_client()
    user_id = session["user_id"]

    try:
        loved_one_id = str(uuid.uuid4())

        db.table("loved_ones").insert({
            "id":                loved_one_id,
            "user_id":           user_id,
            "name":              name,
            "relationship":      relationship,
            "personality_notes": personality_notes,
            "audio_language":    audio_language,
            "message_language":  message_language,
            "cloning_status":    "pending",
        }).execute()

        storage_path = f"{user_id}/{loved_one_id}/sample.mp3"
        db.storage.from_("audio").upload(
            storage_path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )

        db.table("loved_ones").update({
            "audio_sample_path": storage_path
        }).eq("id", loved_one_id).execute()

        return jsonify({
            "success":      True,
            "loved_one_id": loved_one_id,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/clone/<loved_one_id>", methods=["POST"])
@login_required
def clone(loved_one_id: str):
    db      = get_service_client()
    user_id = session["user_id"]

    result = (
        db.table("loved_ones")
        .select("*")
        .eq("id", loved_one_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    loved_one = result.data
    if not loved_one:
        return jsonify({"error": "Not found."}), 404

    try:
        audio_bytes = db.storage.from_("audio").download(
            loved_one["audio_sample_path"]
        )

        voice_id = clone_voice(
            audio_bytes=audio_bytes,
            name=f"{loved_one['name']}",
            description=(
                f"{loved_one['relationship']} — audio in "
                f"{loved_one.get('audio_language', 'English')}"
            ),
        )

        db.table("loved_ones").update({
            "voice_id":       voice_id,
            "cloning_status": "cloned",
        }).eq("id", loved_one_id).execute()

        return jsonify({
            "success":  True,
            "voice_id": voice_id,
            "name":     loved_one["name"],
        })

    except Exception as e:
        db.table("loved_ones").update({
            "cloning_status": "failed"
        }).eq("id", loved_one_id).execute()
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/delete/<loved_one_id>", methods=["POST"])
@login_required
def delete_loved_one(loved_one_id: str):
    db      = get_service_client()
    user_id = session["user_id"]

    result = (
        db.table("loved_ones")
        .select("voice_id, audio_sample_path")
        .eq("id", loved_one_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    loved_one = result.data
    if not loved_one:
        flash("Not found.", "error")
        return redirect(url_for("schedule.dashboard"))

    if loved_one.get("voice_id"):
        delete_voice(loved_one["voice_id"])
    if loved_one.get("audio_sample_path"):
        db.storage.from_("audio").remove([loved_one["audio_sample_path"]])

    db.table("loved_ones").delete().eq("id", loved_one_id).execute()
    flash("Removed successfully.", "success")

@voice_bp.route("/generate/<loved_one_id>", methods=["POST"])
@login_required
def generate_instant(loved_one_id: str):
    """
    Instantly generate a message on demand.
    User can optionally pass a custom prompt / occasion.
    Returns the audio as a signed URL + the script text.
    """
    from app.services.claude import generate_message
    from app.services.elevenlabs import synthesize_speech
    import datetime

    db      = get_service_client()
    user_id = session["user_id"]

    result = (
        db.table("loved_ones")
        .select("*")
        .eq("id", loved_one_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    loved_one = result.data

    if not loved_one:
        return jsonify({"error": "Not found."}), 404

    if not loved_one.get("voice_id"):
        return jsonify({"error": "Voice not cloned yet."}), 400

    # User can optionally send a custom occasion/prompt
    custom_prompt    = request.json.get("custom_prompt", "").strip() if request.is_json else ""
    message_language = loved_one.get("message_language", "English")

    occasion = custom_prompt if custom_prompt else "just thinking of you today"

    # Fetch user's name from profiles
    profile = (
        db.table("profiles")
        .select("full_name")
        .eq("id", user_id)
        .single()
        .execute()
    ).data

    recipient_name = profile.get("full_name", "my dear") if profile else "my dear"

    try:
        # 1. Claude writes the script
        script = generate_message(
            loved_one_name=loved_one["name"],
            relationship=loved_one["relationship"],
            personality_notes=loved_one.get("personality_notes", ""),
            occasion_label=occasion,
            recipient_name=recipient_name,
            message_language=message_language,
        )

        # 2. ElevenLabs synthesizes
        audio_bytes = synthesize_speech(
            voice_id=loved_one["voice_id"],
            text=script,
            language=message_language,
        )

        # 3. Upload to storage
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path = f"generated-audio/{user_id}/{loved_one_id}/instant_{timestamp}.mp3"

        db.storage.from_("audio").upload(
            path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )

        # 4. Signed URL valid for 1 hour
        signed    = db.storage.from_("audio").create_signed_url(path, 3600)
        audio_url = signed["signedURL"]

        # 5. Log to delivered_messages
        db.table("delivered_messages").insert({
            "user_id":      user_id,
            "loved_one_id": loved_one_id,
            "script":       script,
            "audio_path":   path,
        }).execute()

        return jsonify({
            "success":   True,
            "audio_url": audio_url,
            "script":    script,
        })

    except Exception as e:
        print("GENERATE ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
        
    return redirect(url_for("schedule.dashboard"))