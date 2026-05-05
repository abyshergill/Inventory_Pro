"""
Custom decorators for role-based access control.
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

import inspect

def admin_required(f):
    """Restrict route to users with the 'admin' role."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        if inspect.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    """Restrict route to users with 'admin' or 'editor' roles."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        if current_user.role not in ["admin", "editor"]:
            abort(403)
        if inspect.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function