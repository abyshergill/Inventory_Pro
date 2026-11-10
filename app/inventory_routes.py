"""
Inventory CRUD blueprint.
- Admin  : full Create / Update / Delete + column management
- Viewer : read-only search and view
All DB calls use async (aiosqlite).
"""

import os
import json
import re
import uuid
import sqlite3
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app, jsonify, abort,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .decorators import admin_required, editor_required

inv_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

# ────────────────────── Helpers ──────────────────────

def _safe_int(val, default=0):
    """Safely convert value to int, fallback to default if fails."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return default
    try:
        return int(float(val))  # float then int handles '1.0'
    except (ValueError, TypeError):
        return default

def _safe_float(val, default=0.0):
    """Safely convert value to float, fallback to default if fails."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]

def _parse_custom(item: dict) -> dict:
    try:
        return json.loads(item.get("custom_fields") or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}

def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def _collect_form(custom_columns) -> dict:
    """Read + clamp the common item fields from the submitted form."""
    f = request.form
    custom = {c["column_name"]: f.get(f"custom_{c['column_name']}", "").strip()
              for c in custom_columns}
    return {
        "name": f.get("name", "").strip(),
        "description": f.get("description", "").strip(),
        "sku": f.get("sku", "").strip() or None,
        "category": f.get("category", "").strip() or "General",
        "quantity": max(_safe_int(f.get("quantity"), 0), 0),
        "min_quantity": max(_safe_int(f.get("min_quantity"), 0), 0),
        "price": max(_safe_float(f.get("price"), 0.0), 0.0),
        "location": f.get("location", "").strip(),
        "custom": custom,
    }

def _save_image(file) -> str | None:
    """Persist an uploaded image; returns the static-relative path or None."""
    if not (file and file.filename and _allowed_file(file.filename)):
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return f"uploads/{filename}"

def _remove_image(image_path: str):
    if image_path:
        old = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(image_path))
        if os.path.exists(old):
            os.remove(old)

async def _get_custom_columns(db) -> list[dict]:
    return await db.fetch_all("SELECT * FROM custom_columns ORDER BY id")

async def _build_items_query(db, search_term: str | None, search_col: str | None):
    """Build a SELECT that optionally filters by any column."""
    base = "SELECT * FROM inventory_items"
    params: list = []

    fixed_cols = {
        "name", "description", "sku", "category",
        "quantity", "location", "price", "min_quantity",
    }

    if search_term:
        if search_col and search_col in fixed_cols:
            base += f" WHERE CAST({search_col} AS TEXT) LIKE ? ESCAPE '\\'"
            # PostgreSQL: ILIKE $1
            params.append(f"%{_escape_like(search_term)}%")
        elif search_col == "custom":
            base += " WHERE custom_fields LIKE ? ESCAPE '\\'"
            params.append(f"%{_escape_like(search_term)}%")
        else:
            # Global: search across all text columns
            clauses = [f"CAST({c} AS TEXT) LIKE ? ESCAPE '\\'" for c in sorted(fixed_cols)]
            clauses.append("custom_fields LIKE ? ESCAPE '\\'")
            base += " WHERE (" + " OR ".join(clauses) + ")"
            params = [f"%{_escape_like(search_term)}%"] * len(clauses)

    base += " ORDER BY id DESC"
    return base, params

# ────────────────────── Dashboard ──────────────────────

@inv_bp.route("/")
@login_required
async def dashboard():
    db = current_app.config["db"]
    stats = await db.fetch_one(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(quantity), 0) AS units, "
        "COALESCE(SUM(quantity * price), 0) AS value FROM inventory_items"
    )
    critical_rows = await db.fetch_all(
        "SELECT * FROM inventory_items WHERE quantity <= min_quantity ORDER BY quantity ASC"
    )
    categories = await db.fetch_one("SELECT COUNT(DISTINCT category) AS cnt FROM inventory_items")
    recent = await db.fetch_all(
        "SELECT id, name, quantity, category, updated_at FROM inventory_items "
        "ORDER BY updated_at DESC, id DESC LIMIT 5"
    )
    return render_template(
        "dashboard.html",
        total_items=stats["cnt"],
        total_units=stats["units"],
        total_value=stats["value"],
        category_count=categories["cnt"],
        critical_items=critical_rows,
        recent_items=recent,
        is_admin=current_user.is_admin,
        can_edit=(current_user.role in ["admin", "editor"]),
    )

# ────────────────────── List / Search ──────────────────────

@inv_bp.route("/items")
@login_required
async def list_items():
    db = current_app.config["db"]
    search_term = request.args.get("q", "").strip()
    search_col = request.args.get("col", "").strip()

    query, params = await _build_items_query(db, search_term or None, search_col or None)
    items = await db.fetch_all(query, params)
    for item in items:
        item["custom_fields_parsed"] = _parse_custom(item)

    custom_columns = await _get_custom_columns(db)

    return render_template(
        "inventory.html",
        items=items,
        custom_columns=custom_columns,
        search_term=search_term,
        search_col=search_col,
        is_admin=current_user.is_admin,
        can_edit=(current_user.role in ["admin", "editor"]),
    )

# ────────────────────── Create ──────────────────────

def _form_as_item(data: dict) -> dict:
    """Re-shape submitted data so the form can be re-rendered after an error."""
    item = {k: v for k, v in data.items() if k != "custom"}
    item["custom_fields_parsed"] = data["custom"]
    item.setdefault("image_path", "")
    return item

@inv_bp.route("/items/new", methods=["GET", "POST"])
@editor_required
async def create_item():
    db = current_app.config["db"]
    custom_columns = await _get_custom_columns(db)
    prefill = None

    if request.method == "POST":
        data = _collect_form(custom_columns)
        prefill = _form_as_item(data)
        if not data["name"]:
            flash("Item name is required.", "danger")
        else:
            image_path = _save_image(request.files.get("image")) or ""
            try:
                await db.execute(
                    """INSERT INTO inventory_items
                       (name, description, sku, category, quantity, min_quantity,
                        price, location, image_path, custom_fields)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data["name"], data["description"], data["sku"], data["category"],
                        data["quantity"], data["min_quantity"], data["price"],
                        data["location"], image_path, json.dumps(data["custom"]),
                    ),
                )
                flash("Item created successfully!", "success")
                return redirect(url_for("inventory.list_items"))
            except sqlite3.IntegrityError as e:
                _remove_image(image_path)
                if "sku" in str(e).lower():
                    flash(f"SKU '{data['sku']}' already exists.", "danger")
                else:
                    flash("Could not save the item (database constraint).", "danger")
            except Exception:
                _remove_image(image_path)
                current_app.logger.exception("create_item failed")
                flash("Unexpected error while saving the item.", "danger")

    return render_template("item_form.html", item=prefill, custom_columns=custom_columns,
                           is_admin=current_user.is_admin, can_edit=True)

# ────────────────────── Update ──────────────────────

@inv_bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@editor_required
async def edit_item(item_id: int):
    db = current_app.config["db"]
    item = await db.fetch_one("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
    # PostgreSQL: WHERE id = $1
    if not item:
        abort(404)

    custom_columns = await _get_custom_columns(db)
    item["custom_fields_parsed"] = _parse_custom(item)

    if request.method == "POST":
        data = _collect_form(custom_columns)
        shown = _form_as_item(data)
        shown["id"] = item_id
        shown["image_path"] = item["image_path"]
        if not data["name"]:
            flash("Item name is required.", "danger")
            item = shown
        else:
            old_image = item["image_path"]
            new_image = _save_image(request.files.get("image"))
            image_path = new_image or old_image
            try:
                await db.execute(
                    """UPDATE inventory_items
                       SET name=?, description=?, sku=?, category=?,
                           quantity=?, min_quantity=?, price=?, location=?,
                           image_path=?, custom_fields=?, updated_at=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (
                        data["name"], data["description"], data["sku"], data["category"],
                        data["quantity"], data["min_quantity"], data["price"],
                        data["location"], image_path, json.dumps(data["custom"]), item_id,
                    ),
                )
                if new_image:
                    _remove_image(old_image)
                flash("Item updated.", "success")
                return redirect(url_for("inventory.list_items"))
            except sqlite3.IntegrityError as e:
                _remove_image(new_image or "")
                item = shown
                if "sku" in str(e).lower():
                    flash(f"SKU '{data['sku']}' already exists.", "danger")
                else:
                    flash("Could not save the item (database constraint).", "danger")
            except Exception:
                _remove_image(new_image or "")
                item = shown
                current_app.logger.exception("edit_item failed")
                flash("Unexpected error while saving the item.", "danger")

    return render_template("item_form.html", item=item, custom_columns=custom_columns,
                           is_admin=current_user.is_admin, can_edit=True)

# ────────────────────── Delete ──────────────────────

@inv_bp.route("/items/<int:item_id>/delete", methods=["POST"])
@editor_required
async def delete_item(item_id: int):
    db = current_app.config["db"]
    item = await db.fetch_one("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
    if not item:
        abort(404)
    await db.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
    _remove_image(item.get("image_path"))
    flash("Item deleted.", "info")
    return redirect(url_for("inventory.list_items"))

# ────────────────── Custom Columns (Dynamic) ──────────────────

@inv_bp.route("/columns", methods=["GET", "POST"])
@admin_required
async def manage_columns():
    db = current_app.config["db"]

    if request.method == "POST":
        action = request.form.get("action")
        raw = request.form.get("column_name", "").strip().lower()
        col_name = re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")
        col_type = request.form.get("column_type", "text")
        if col_type not in ("text", "number", "date"):
            col_type = "text"

        if action == "add":
            if not col_name:
                flash("Column name must contain letters or numbers.", "danger")
            else:
                try:
                    await db.execute(
                        "INSERT INTO custom_columns (column_name, column_type) VALUES (?, ?)",
                        (col_name, col_type),
                    )
                    flash(f"Column '{col_name}' added.", "success")
                except sqlite3.IntegrityError:
                    flash(f"Column '{col_name}' already exists.", "warning")

        elif action == "delete":
            col_id = _safe_int(request.form.get("column_id"), -1)
            await db.execute("DELETE FROM custom_columns WHERE id = ?", (col_id,))
            flash("Column removed.", "info")

        return redirect(url_for("inventory.manage_columns"))

    columns = await _get_custom_columns(db)
    return render_template("manage_columns.html", custom_columns=columns, is_admin=True, can_edit=True)

# ────────────────── API: JSON search (AJAX) ──────────────────

@inv_bp.route("/api/search")
@login_required
async def api_search():
    db = current_app.config["db"]
    q = request.args.get("q", "").strip()
    col = request.args.get("col", "").strip()
    query, params = await _build_items_query(db, q or None, col or None)
    items = await db.fetch_all(query, params)
    for item in items:
        item["custom_fields_parsed"] = _parse_custom(item)
    return jsonify(items)
