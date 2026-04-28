from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from app.blueprints.utils import login_required
from app.db.client import get_service_client

schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/")
@schedule_bp.route("/dashboard")
@login_required
def dashboard():
    db      = get_service_client()
    user_id = session["user_id"]

    loved_ones = (
        db.table("loved_ones")
        .select("*, memory_dates(*)")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    ).data

    return render_template(
        "dashboard/index.html",
        loved_ones=loved_ones,
        user_email=session.get("user_email"),
    )


@schedule_bp.route("/memory-date", methods=["POST"])
@login_required
def add_memory_date():
    db      = get_service_client()
    user_id = session["user_id"]

    loved_one_id = request.form.get("loved_one_id", "").strip()
    label        = request.form.get("label", "").strip()
    month        = request.form.get("month", "").strip()
    day          = request.form.get("day", "").strip()

    if not all([loved_one_id, label, month, day]):
        flash("All fields are required.", "error")
        return redirect(url_for("schedule.dashboard"))

    try:
        month_int = int(month)
        day_int   = int(day)

        if not (1 <= month_int <= 12) or not (1 <= day_int <= 31):
            flash("Invalid date.", "error")
            return redirect(url_for("schedule.dashboard"))

        db.table("memory_dates").insert({
            "user_id":      user_id,
            "loved_one_id": loved_one_id,
            "label":        label,
            "month":        month_int,
            "day":          day_int,
        }).execute()

        flash(f"Memory date added: {label}", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for("schedule.dashboard"))


@schedule_bp.route("/memory-date/<date_id>/delete", methods=["POST"])
@login_required
def delete_memory_date(date_id: str):
    db      = get_service_client()
    user_id = session["user_id"]

    db.table("memory_dates").delete()\
        .eq("id", date_id)\
        .eq("user_id", user_id)\
        .execute()

    flash("Memory date removed.", "success")
    return redirect(url_for("schedule.dashboard"))