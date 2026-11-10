"""
Application factory – assembles Flask, extensions, blueprints.
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from .config import load_config
from .database import init_db_sync, SQLiteDatabase
from .models import User

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_path: str = "config/secrets.ini") -> Flask:
    app = Flask(__name__)

    # ── Load config from INI ──
    cfg = load_config(config_path)
    app.config.update(cfg)
    if app.config["SECRET_KEY"] in ("dev-fallback-key", "CHANGE-ME-to-a-long-random-string"):
        import warnings
        warnings.warn("Insecure SECRET_KEY in use - set a long random value in secrets.ini")
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    # ── Ensure directories exist ──
    db_dir = os.path.dirname(app.config["DATABASE_PATH"])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Initialise database tables (synchronous, runs once) ──
    init_db_sync(app.config["DATABASE_PATH"])

    # ── Attach async DB helper to app config ──
    app.config["db"] = SQLiteDatabase(app.config["DATABASE_PATH"])
    # For PostgreSQL:
    # from .database import PostgreSQLDatabase
    # app.config["db"] = PostgreSQLDatabase(app.config["POSTGRESQL_DSN"])

    # ── Extensions ──
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    csrf.init_app(app)

    # ── User loader (synchronous – required by Flask-Login) ──
    import sqlite3

    @login_manager.user_loader
    def load_user(user_id):
        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return User(dict(row)) if row else None
        # PostgreSQL equivalent:
        # row = psycopg2_conn.execute(
        #     "SELECT * FROM users WHERE id = %s", (user_id,)
        # ).fetchone()

    # ── Register blueprints ──
    from .auth_routes import auth_bp
    from .inventory_routes import inv_bp
    from .user_routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inv_bp)
    app.register_blueprint(user_bp)

    # ── Error pages ──
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, title="Access denied",
                               message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, title="Page not found",
                               message="The page you are looking for doesn't exist."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413, title="File too large",
                               message="The uploaded file exceeds the size limit."), 413

    # ── Root route ──
    from flask import redirect, url_for
    @app.route("/")
    def index():
        return redirect(url_for("inventory.dashboard"))

    return app