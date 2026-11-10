"""
Authentication blueprint – register, login, logout.
The first registered user automatically becomes admin.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from .models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
async def register():
    db = current_app.config["db"]
    # Check if any users exist
    count = await db.fetch_one("SELECT COUNT(*) as cnt FROM users")
    if count["cnt"] > 0:
        flash("Registration is disabled. Please contact an administrator.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))
        
        # ... rest of validation ...
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("auth.register"))

        # First user is always admin
        role = "admin"
        pw_hash = generate_password_hash(password)
        try:
            await db.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, pw_hash, role),
            )
            flash("Admin account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash("Could not create the account. Username or email may already exist.", "danger")
            return redirect(url_for("auth.register"))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
async def login():
    if current_user.is_authenticated:
        return redirect(url_for("inventory.dashboard"))
    db = current_app.config["db"]
    if request.method == "GET":
        count = await db.fetch_one("SELECT COUNT(*) as cnt FROM users")
        if count["cnt"] == 0:
            return redirect(url_for("auth.register"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        row = await db.fetch_one(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        # PostgreSQL: WHERE username = $1
        if row and check_password_hash(row["password_hash"], password):
            user = User(row)
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("inventory.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))