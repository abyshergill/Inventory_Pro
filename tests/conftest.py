"""
Pytest fixtures for the Inventory Management app.
Creates a fresh temp database for every test session.
"""

import os
import sys
import tempfile
import configparser
import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app

@pytest.fixture()
def _config_file():
    """Write a temporary secrets.ini for testing."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_inventory.db")
    upload_dir = os.path.join(tmp_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    cfg = configparser.ConfigParser()
    cfg["app"] = {
        "secret_key": "test-secret-key-1234",
        "debug": "true",
        "host": "127.0.0.1",
        "port": "5000",
    }
    cfg["database"] = {
        "type": "sqlite",
        "sqlite_path": db_path,
    }
    cfg["uploads"] = {
        "max_file_size_mb": "2",
        "allowed_extensions": "png,jpg,jpeg,gif,webp",
        "upload_folder": upload_dir,
    }

    ini_path = os.path.join(tmp_dir, "test_secrets.ini")
    with open(ini_path, "w") as f:
        cfg.write(f)

    return ini_path

@pytest.fixture()
def app(_config_file):
    """Create application for testing."""
    application = create_app(config_path=_config_file)
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False  # disable CSRF for test convenience
    return application

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

def _register_and_login(client, username="admin", email="admin@test.com",
                         password="secret123"):
    """Helper: register then log in, return response."""
    client.post("/auth/register", data={
        "username": username,
        "email": email,
        "password": password,
    })
    return client.post("/auth/login", data={
        "username": username,
        "password": password,
    }, follow_redirects=True)

@pytest.fixture()
def admin_client(client):
    """A client already logged in as admin (first user)."""
    _register_and_login(client, "admin", "admin@test.com", "secret123")
    return client

@pytest.fixture()
def viewer_client(client):
    """Register admin first (so it exists), then register + login as viewer."""
    # ensure admin exists first
    client.post("/auth/register", data={
        "username": "admin2",
        "email": "admin2@test.com",
        "password": "secret123",
    })
    _register_and_login(client, "viewer", "viewer@test.com", "viewerpass")
    return client