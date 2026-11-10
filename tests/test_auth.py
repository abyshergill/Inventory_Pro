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

def test_login_redirects_to_register_on_fresh_install(client):
    resp = client.get("/auth/login", follow_redirects=True)
    assert b"Create your account" in resp.data

def test_login_page_loads(client):
    client.post("/auth/register", data={"username": "a", "email": "a@test.com", "password": "password1"})
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

def test_registration_closed_after_first_user(client):
    client.post("/auth/register", data={"username": "u1", "email": "u1@test.com", "password": "password1"})
    resp = client.post("/auth/register", data={
        "username": "u2", "email": "u2@test.com", "password": "password2",
    }, follow_redirects=True)
    assert b"Registration is disabled" in resp.data

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
    resp = admin_client.post("/auth/logout", follow_redirects=True)
    assert b"logged out" in resp.data.lower() or b"Log In" in resp.data

def test_short_password_rejected(client):
    resp = client.post("/auth/register", data={
        "username": "shortpw",
        "email": "short@test.com",
        "password": "12",
    }, follow_redirects=True)
    assert b"at least 6" in resp.data.lower() or b"required" in resp.data.lower()

def test_duplicate_username_rejected(admin_client):
    data = {"username": "dupe", "email": "d1@test.com", "password": "password1", "role": "viewer"}
    admin_client.post("/users/new", data=data)
    data["email"] = "d2@test.com"
    resp = admin_client.post("/users/new", data=data, follow_redirects=True)
    assert b"already taken" in resp.data

def test_invalid_role_rejected(admin_client):
    resp = admin_client.post("/users/new", data={
        "username": "x", "email": "x@test.com", "password": "password1", "role": "superuser",
    }, follow_redirects=True)
    assert b"Invalid role" in resp.data

def test_cannot_demote_or_delete_last_admin(admin_client):
    resp = admin_client.post("/users/1/edit", data={
        "username": "admin", "email": "admin@test.com", "role": "viewer",
    }, follow_redirects=True)
    assert b"last remaining admin" in resp.data
    resp = admin_client.post("/users/1/delete", follow_redirects=True)
    assert b"cannot delete your own" in resp.data.lower()

def test_edit_user_email_clash(admin_client):
    admin_client.post("/users/new", data={"username": "b", "email": "b@test.com",
                                          "password": "password1", "role": "viewer"})
    resp = admin_client.post("/users/2/edit", data={"username": "b", "email": "admin@test.com",
                                                    "role": "viewer"}, follow_redirects=True)
    assert b"already taken" in resp.data

def test_404_page_renders_for_logged_in_user(admin_client):
    resp = admin_client.get("/nope")
    assert resp.status_code == 404
    assert b"Page not found" in resp.data
