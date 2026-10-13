"""
RPGMS Authentication Blueprint
File: app/blueprints/auth.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.auth import authenticate_user, login_user, logout_user, get_current_user
from app.utils import is_safe_url

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    return_to = request.args.get("return_to", "")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        post_return_to = request.form.get("return_to", "")

        user = authenticate_user(username, password)
        if user:
            login_user(user)
            flash(f"Welcome back, {user['display_name']}!", "success")
            target = post_return_to if post_return_to and is_safe_url(post_return_to) else url_for("dashboard.index")
            return redirect(target)
        else:
            flash("Incorrect username or password.", "danger")

    is_demo = current_app.config.get("APP_ENV") == "demo"
    return render_template("auth/login.html", is_demo=is_demo, return_to=return_to)

@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/")
def index():
    if get_current_user():
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))
