from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for


auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("views.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if (
            username == current_app.config["ADMIN_USERNAME"]
            and password == current_app.config["ADMIN_PASSWORD"]
        ):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(request.args.get("next") or url_for("views.dashboard"))
        flash("Invalid admin credentials.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
