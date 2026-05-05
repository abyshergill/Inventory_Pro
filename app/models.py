"""
User model for Flask-Login integration.
"""

from flask_login import UserMixin

class User(UserMixin):
    """Wraps a database row dict so Flask-Login can use it."""

    def __init__(self, row: dict):
        self._data = row

    # ── Flask-Login required ──
    def get_id(self):
        return str(self._data["id"])

    # ── Convenience properties ──
    @property
    def id(self):
        return self._data["id"]

    @property
    def username(self):
        return self._data["username"]

    @property
    def email(self):
        return self._data["email"]

    @property
    def password_hash(self):
        return self._data["password_hash"]

    @property
    def role(self):
        return self._data.get("role", "viewer")

    @property
    def is_admin(self):
        return self.role == "admin"