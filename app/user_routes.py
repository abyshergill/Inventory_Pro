"""
User management blueprint for Admins.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from .models import User
from .decorators import admin_required

user_bp = Blueprint("users", __name__, url_prefix="/users")

VALID_ROLES = ("admin", "editor", "viewer")
MIN_PASSWORD = 6

async def _admin_count(db) -> int:
    row = await db.fetch_one("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'")
    return row["cnt"]

@user_bp.route("/")
@admin_required
async def list_users():
    db = current_app.config["db"]
    users = await db.fetch_all("SELECT * FROM users ORDER BY id DESC")
    return render_template("users/list.html", users=users)

@user_bp.route("/new", methods=["GET", "POST"])
@admin_required
async def create_user():
    if request.method == "POST":
        db = current_app.config["db"]
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "viewer")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("users.create_user"))
        if role not in VALID_ROLES:
            flash("Invalid role.", "danger")
            return redirect(url_for("users.create_user"))
        if len(password) < MIN_PASSWORD:
            flash(f"Password must be at least {MIN_PASSWORD} characters.", "danger")
            return redirect(url_for("users.create_user"))

        existing = await db.fetch_one(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email),
        )
        if existing:
            flash("Username or email already taken.", "danger")
            return redirect(url_for("users.create_user"))

        pw_hash = generate_password_hash(password)
        await db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, role),
        )
        flash(f"User '{username}' created successfully.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", user=None)

@user_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
async def edit_user(user_id: int):
    db = current_app.config["db"]
    row = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not row:
        abort(404)
    
    user = User(row)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "viewer")
        password = request.form.get("password")

        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for("users.edit_user", user_id=user_id))
        if role not in VALID_ROLES:
            flash("Invalid role.", "danger")
            return redirect(url_for("users.edit_user", user_id=user_id))
        if password and len(password) < MIN_PASSWORD:
            flash(f"Password must be at least {MIN_PASSWORD} characters.", "danger")
            return redirect(url_for("users.edit_user", user_id=user_id))
        clash = await db.fetch_one(
            "SELECT id FROM users WHERE (username = ? OR email = ?) AND id != ?",
            (username, email, user_id),
        )
        if clash:
            flash("Username or email already taken.", "danger")
            return redirect(url_for("users.edit_user", user_id=user_id))
        if user.role == "admin" and role != "admin" and await _admin_count(db) <= 1:
            flash("Cannot demote the last remaining admin.", "danger")
            return redirect(url_for("users.edit_user", user_id=user_id))

        # Update user
        if password:
            pw_hash = generate_password_hash(password)
            await db.execute(
                "UPDATE users SET username=?, email=?, role=?, password_hash=? WHERE id=?",
                (username, email, role, pw_hash, user_id),
            )
        else:
            await db.execute(
                "UPDATE users SET username=?, email=?, role=? WHERE id=?",
                (username, email, role, user_id),
            )
        
        flash(f"User '{username}' updated.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", user=user)

@user_bp.route("/<int:user_id>/delete", methods=["POST"])
@admin_required
async def delete_user(user_id: int):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.list_users"))
    
    db = current_app.config["db"]
    target = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not target:
        abort(404)
    if target["role"] == "admin" and await _admin_count(db) <= 1:
        flash("Cannot delete the last remaining admin.", "danger")
        return redirect(url_for("users.list_users"))
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    flash("User deleted.", "info")
    return redirect(url_for("users.list_users"))
