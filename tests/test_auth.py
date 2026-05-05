"""
Tests for authentication: register, login, logout, role assignment.
"""

def test_root_redirects_to_dashboard(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/inventory/" in resp.location

def test_register_page_loads(client):
    resp = client.get("/auth/register")
    assert resp.status_code == 200
    assert b"Register" in resp.data

def test_login_page_loads(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"Log In" in resp.data

def test_register_first_user_becomes_admin(client):
    resp = client.post("/auth/register", data={
        "username": "firstuser",
        "email": "first@test.com",
        "password": "password123",
    }, follow_redirects=True)
    assert b"admin" in resp.data.lower()

def test_register_second_user_becomes_viewer(client):
    # First user = admin
    client.post("/auth/register", data={
        "username": "u1",
        "email": "u1@test.com",
        "password": "password1",
    })
    resp = client.post("/auth/register", data={
        "username": "u2",
        "email": "u2@test.com",
        "password": "password2",
    }, follow_redirects=True)
    assert b"viewer" in resp.data.lower()

def test_login_valid_credentials(client):
    client.post("/auth/register", data={
        "username": "logintest",
        "email": "login@test.com",
        "password": "mypassword",
    })
    resp = client.post("/auth/login", data={
        "username": "logintest",
        "password": "mypassword",
    }, follow_redirects=True)
    assert b"Welcome back" in resp.data or b"Dashboard" in resp.data

def test_login_invalid_credentials(client):
    resp = client.post("/auth/login", data={
        "username": "nonexistent",
        "password": "wrong",
    }, follow_redirects=True)
    assert b"Invalid" in resp.data

def test_logout(admin_client):
    resp = admin_client.get("/auth/logout", follow_redirects=True)
    assert b"logged out" in resp.data.lower() or b"Log In" in resp.data

def test_short_password_rejected(client):
    resp = client.post("/auth/register", data={
        "username": "shortpw",
        "email": "short@test.com",
        "password": "12",
    }, follow_redirects=True)
    assert b"at least 6" in resp.data.lower() or b"required" in resp.data.lower()

def test_duplicate_username_rejected(client):
    client.post("/auth/register", data={
        "username": "dupeuser",
        "email": "dupe1@test.com",
        "password": "password1",
    })
    resp = client.post("/auth/register", data={
        "username": "dupeuser",
        "email": "dupe2@test.com",
        "password": "password2",
    }, follow_redirects=True)
    assert b"already taken" in resp.data.lower() or b"already" in resp.data.lower()