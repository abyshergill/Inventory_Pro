"""
Inventory CRUD blueprint.
- Admin  : full Create / Update / Delete + column management
- Viewer : read-only search and view
All DB calls use async (aiosqlite).
"""

import os
import json
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
            base += f" WHERE {search_col} LIKE ?"
            # PostgreSQL: ILIKE $1
            params.append(f"%{search_term}%")
        elif search_col == "custom":
            base += " WHERE custom_fields LIKE ?"
            params.append(f"%{search_term}%")
        else:
            # Global: search across all text columns
            clauses = [f"{c} LIKE ?" for c in fixed_cols]
            clauses.append("custom_fields LIKE ?")
            base += " WHERE (" + " OR ".join(clauses) + ")"
            params = [f"%{search_term}%"] * len(clauses)

    base += " ORDER BY id DESC"
    return base, params

# ────────────────────── Dashboard ──────────────────────

@inv_bp.route("/")
@login_required
async def dashboard():
    db = current_app.config["db"]
    total = await db.fetch_one("SELECT COUNT(*) as cnt FROM inventory_items")
    critical_rows = await db.fetch_all(
        "SELECT * FROM inventory_items WHERE quantity <= min_quantity"
    )
    return render_template(
        "dashboard.html",
        total_items=total["cnt"],
        critical_items=critical_rows,
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

    # Parse custom_fields JSON for template
    for item in items:
        try:
            item["custom_fields_parsed"] = json.loads(item.get("custom_fields", "{}"))
        except (json.JSONDecodeError, TypeError):
            item["custom_fields_parsed"] = {}

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

@inv_bp.route("/items/new", methods=["GET", "POST"])
@editor_required
async def create_item():
    db = current_app.config["db"]
    custom_columns = await _get_custom_columns(db)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Item name is required.", "danger")
            return redirect(url_for("inventory.create_item"))

        # Handle image upload
        image_path = ""
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and _allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[-1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_path = f"uploads/{filename}"

        # Collect custom fields
        custom_data = {}
        for col in custom_columns:
            val = request.form.get(f"custom_{col['column_name']}", "")
            custom_data[col["column_name"]] = val

        # SKU: Convert blank string to None so multiple blanks don't trigger UNIQUE error
        sku_val = request.form.get("sku", "").strip() or None

        try:
            await db.execute(
                """INSERT INTO inventory_items
                   (name, description, sku, category, quantity, min_quantity,
                    price, location, image_path, custom_fields)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name,
                    request.form.get("description", ""),
                    sku_val,
                    request.form.get("category", "General"),
                    _safe_int(request.form.get("quantity"), 0),
                    _safe_int(request.form.get("min_quantity"), 0),
                    _safe_float(request.form.get("price"), 0.0),
                    request.form.get("location", ""),
                    image_path,
                    json.dumps(custom_data),
                ),
            )
            flash("Item created successfully!", "success")
            return redirect(url_for("inventory.list_items"))
        except sqlite3.IntegrityError as e:
            if "sku" in str(e).lower():
                flash(f"Error: SKU '{sku_val}' already exists.", "danger")
            else:
                flash(f"Database error: {e}", "danger")
        except Exception as e:
            flash(f"Unexpected error: {e}", "danger")

    return render_template("item_form.html", item=None, custom_columns=custom_columns, is_admin=current_user.is_admin, can_edit=True)

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

    if request.method == "POST":
        image_path = item["image_path"]
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and _allowed_file(file.filename):
                # Delete old image
                if image_path:
                    old = os.path.join(current_app.config["UPLOAD_FOLDER"],
                                       os.path.basename(image_path))
                    if os.path.exists(old):
                        os.remove(old)
                ext = file.filename.rsplit(".", 1)[-1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_path = f"uploads/{filename}"

        custom_data = {}
        for col in custom_columns:
            custom_data[col["column_name"]] = request.form.get(
                f"custom_{col['column_name']}", ""
            )

        # SKU: Convert blank string to None
        sku_val = request.form.get("sku", "").strip() or None

        try:
            await db.execute(
                """UPDATE inventory_items
                   SET name=?, description=?, sku=?, category=?,
                       quantity=?, min_quantity=?, price=?, location=?,
                       image_path=?, custom_fields=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    request.form.get("name", "").strip(),
                    request.form.get("description", ""),
                    sku_val,
                    request.form.get("category", "General"),
                    _safe_int(request.form.get("quantity"), 0),
                    _safe_int(request.form.get("min_quantity"), 0),
                    _safe_float(request.form.get("price"), 0.0),
                    request.form.get("location", ""),
                    image_path,
                    json.dumps(custom_data),
                    item_id,
                ),
            )
            flash("Item updated.", "success")
            return redirect(url_for("inventory.list_items"))
        except sqlite3.IntegrityError as e:
            if "sku" in str(e).lower():
                flash(f"Error: SKU '{sku_val}' already exists.", "danger")
            else:
                flash(f"Database error: {e}", "danger")
        except Exception as e:
            flash(f"Unexpected error: {e}", "danger")

    try:
        item["custom_fields_parsed"] = json.loads(item.get("custom_fields", "{}"))
    except (json.JSONDecodeError, TypeError):
        item["custom_fields_parsed"] = {}

    return render_template(
        "item_form.html", item=item, custom_columns=custom_columns, is_admin=current_user.is_admin, can_edit=True
    )

# ────────────────────── Delete ──────────────────────

@inv_bp.route("/items/<int:item_id>/delete", methods=["POST"])
@editor_required
async def delete_item(item_id: int):
    db = current_app.config["db"]
    item = await db.fetch_one("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
    if not item:
        abort(404)
    # Remove image file
    if item.get("image_path"):
        img = os.path.join(
            current_app.config["UPLOAD_FOLDER"], os.path.basename(item["image_path"])
        )
        if os.path.exists(img):
            os.remove(img)
    await db.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
    flash("Item deleted.", "info")
    return redirect(url_for("inventory.list_items"))

# ────────────────── Custom Columns (Dynamic) ──────────────────

@inv_bp.route("/columns", methods=["GET", "POST"])
@admin_required
async def manage_columns():
    db = current_app.config["db"]

    if request.method == "POST":
        action = request.form.get("action")
        col_name = request.form.get("column_name", "").strip().lower().replace(" ", "_")
        col_type = request.form.get("column_type", "text")

        if action == "add" and col_name:
            try:
                await db.execute(
                    "INSERT INTO custom_columns (column_name, column_type) VALUES (?, ?)",
                    (col_name, col_type),
                )
                flash(f"Column '{col_name}' added.", "success")
            except Exception:
                flash(f"Column '{col_name}' already exists.", "warning")

        elif action == "delete":
            col_id = request.form.get("column_id")
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
        try:
            item["custom_fields_parsed"] = json.loads(item.get("custom_fields", "{}"))
        except (json.JSONDecodeError, TypeError):
            item["custom_fields_parsed"] = {}
    return jsonify(items)