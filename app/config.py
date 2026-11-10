"""
Read the INI secrets file and produce a flat dict that Flask can consume.
PostgreSQL DSN (Data Source Name) is built automatically when the DB type
is set to 'postgresql' in secrets.ini.
"""

import configparser
import os

def load_config(config_path: str = "config/secrets.ini") -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Copy config/secrets.example.ini → config/secrets.ini and edit it."
        )

    parser = configparser.ConfigParser()
    parser.read(config_path)

    # Relative paths in the INI resolve against the project root, not the CWD
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _abs(path: str) -> str:
        return path if os.path.isabs(path) else os.path.join(root, path)

    db_type = parser.get("database", "type", fallback="sqlite")
    sqlite_path = parser.get("database", "sqlite_path", fallback="data/inventory.db")

    # ── PostgreSQL DSN (built only when type == postgresql) ──
    # pg_host = parser.get("database", "host", fallback="localhost")
    # pg_port = parser.get("database", "port", fallback="5432")
    # pg_name = parser.get("database", "name", fallback="inventory_db")
    # pg_user = parser.get("database", "user", fallback="postgres")
    # pg_pass = parser.get("database", "password", fallback="")
    # postgresql_dsn = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_name}"

    upload_folder = parser.get("uploads", "upload_folder", fallback="app/static/uploads")
    max_size_mb = parser.getint("uploads", "max_file_size_mb", fallback=16)
    allowed_ext = parser.get("uploads", "allowed_extensions", fallback="png,jpg,jpeg,gif,webp")

    return {
        "SECRET_KEY": parser.get("app", "secret_key", fallback="dev-fallback-key"),
        "DEBUG": parser.getboolean("app", "debug", fallback=False),
        "HOST": parser.get("app", "host", fallback="127.0.0.1"),
        "PORT": parser.getint("app", "port", fallback=5000),
        "DB_TYPE": db_type,
        "DATABASE_PATH": _abs(sqlite_path),
        # "POSTGRESQL_DSN": postgresql_dsn,   # uncomment for PostgreSQL
        "UPLOAD_FOLDER": _abs(upload_folder),
        "MAX_CONTENT_LENGTH": max_size_mb * 1024 * 1024,
        "ALLOWED_EXTENSIONS": {e.strip().lower() for e in allowed_ext.split(",") if e.strip()},
    }