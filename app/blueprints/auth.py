from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from app.db.client import get_service_client

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _save_session(user, session_data):
    session["user_id"]      = user.id
    session["user_email"]   = user.email
    session["access_token"] = session_data.access_token


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("auth/signup.html")

    email     = request.form.get("email", "").strip()
    password  = request.form.get("password", "").strip()
    full_name = request.form.get("full_name", "").strip()

    if not email or not password:
        flash("Email and password are required.", "error")
        return render_template("auth/signup.html")

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return render_template("auth/signup.html")

    try:
        db       = get_service_client()
        response = db.auth.sign_up({
            "email":    email,
            "password": password,
            "options":  {"data": {"full_name": full_name}},
        })

        if response.user and response.session:
            _save_session(response.user, response.session)
            return redirect(url_for("journal.write"))  # ← fixed

        if response.user and not response.session:
            flash("Account created! Please sign in.", "info")
            return render_template("auth/signup.html")

        flash("Signup failed. Email may already be in use.", "error")

    except Exception as e:
        print("SIGNUP ERROR:", str(e))
        flash(f"Error: {str(e)}", "error")

    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        flash("Email and password are required.", "error")
        return render_template("auth/login.html")

    try:
        db       = get_service_client()
        response = db.auth.sign_in_with_password({
            "email": email, "password": password
        })

        if response.user and response.session:
            _save_session(response.user, response.session)
            return redirect(url_for("journal.write"))  # ← fixed

        flash("Invalid email or password.", "error")

    except Exception as e:
        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))