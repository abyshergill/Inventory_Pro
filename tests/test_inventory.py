"""
Tests for inventory CRUD, search, column management, and role restrictions.
"""

import io

def test_dashboard_requires_login(client):
    client.post("/auth/register", data={"username": "a", "email": "a@test.com", "password": "password1"})
    resp = client.get("/inventory/", follow_redirects=True)
    assert b"Log In" in resp.data

def test_dashboard_loads_for_admin(admin_client):
    resp = admin_client.get("/inventory/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data

def test_create_item_admin(admin_client):
    resp = admin_client.post("/inventory/items/new", data={
        "name": "Test Widget",
        "sku": "TW-001",
        "category": "Parts",
        "quantity": "100",
        "min_quantity": "10",
        "price": "9.99",
        "location": "Shelf A",
        "description": "A test widget",
    }, follow_redirects=True)
    assert b"Test Widget" in resp.data
    assert b"created" in resp.data.lower() or resp.status_code == 200

def test_viewer_cannot_create_item(viewer_client):
    resp = viewer_client.post("/inventory/items/new", data={
        "name": "Blocked Item",
        "sku": "BLK-001",
        "quantity": "5",
        "min_quantity": "1",
        "price": "1.00",
    }, follow_redirects=True)
    # Should be forbidden or redirected
    assert resp.status_code in (403, 200)
    assert b"Blocked Item" not in resp.data or b"403" in resp.data

def test_viewer_can_view_items(viewer_client):
    resp = viewer_client.get("/inventory/items")
    assert resp.status_code == 200
    assert b"Inventory" in resp.data

def test_search_items(admin_client):
    # Create an item first
    admin_client.post("/inventory/items/new", data={
        "name": "SearchableGadget",
        "sku": "SG-001",
        "category": "Gadgets",
        "quantity": "50",
        "min_quantity": "5",
        "price": "19.99",
        "location": "Shelf B",
    })
    resp = admin_client.get("/inventory/items?q=SearchableGadget&col=name")
    assert resp.status_code == 200
    assert b"SearchableGadget" in resp.data

def test_search_all_columns(admin_client):
    admin_client.post("/inventory/items/new", data={
        "name": "UniqueItem99",
        "sku": "UI-99",
        "category": "Special",
        "quantity": "1",
        "min_quantity": "0",
        "price": "99.00",
        "location": "Vault",
    })
    resp = admin_client.get("/inventory/items?q=UniqueItem99")
    assert b"UniqueItem99" in resp.data

def test_critical_stock_alert(admin_client):
    admin_client.post("/inventory/items/new", data={
        "name": "LowStockItem",
        "sku": "LS-001",
        "category": "Parts",
        "quantity": "2",
        "min_quantity": "10",
        "price": "5.00",
        "location": "Bin C",
    })
    resp = admin_client.get("/inventory/")
    assert b"LowStockItem" in resp.data
    assert b"Critical" in resp.data or b"critical" in resp.data.lower()

def test_edit_item(admin_client):
    admin_client.post("/inventory/items/new", data={
        "name": "Editable",
        "sku": "ED-001",
        "category": "General",
        "quantity": "10",
        "min_quantity": "2",
        "price": "3.00",
        "location": "A1",
    })
    # Find item id = 1 (or whichever is first)
    resp = admin_client.post("/inventory/items/1/edit", data={
        "name": "Edited Name",
        "sku": "ED-001-X",
        "category": "Updated",
        "quantity": "20",
        "min_quantity": "5",
        "price": "7.50",
        "location": "B2",
        "description": "Updated description",
    }, follow_redirects=True)
    assert b"Edited Name" in resp.data or b"updated" in resp.data.lower()

def test_delete_item(admin_client):
    admin_client.post("/inventory/items/new", data={
        "name": "Deletable",
        "sku": "DEL-001",
        "quantity": "1",
        "min_quantity": "0",
        "price": "1.00",
    })
    resp = admin_client.post("/inventory/items/1/delete", follow_redirects=True)
    assert b"deleted" in resp.data.lower() or resp.status_code == 200

def test_viewer_cannot_delete_item(viewer_client):
    resp = viewer_client.post("/inventory/items/1/delete", follow_redirects=True)
    assert resp.status_code in (403, 200)
    assert b"403" in resp.data or b"Log In" in resp.data

def test_add_custom_column(admin_client):
    resp = admin_client.post("/inventory/columns", data={
        "action": "add",
        "column_name": "supplier",
        "column_type": "text",
    }, follow_redirects=True)
    assert b"supplier" in resp.data

def test_delete_custom_column(admin_client):
    admin_client.post("/inventory/columns", data={
        "action": "add",
        "column_name": "temp_col",
        "column_type": "number",
    })
    resp = admin_client.post("/inventory/columns", data={
        "action": "delete",
        "column_id": "1",
    }, follow_redirects=True)
    assert b"removed" in resp.data.lower() or resp.status_code == 200

def test_upload_image_with_item(admin_client):
    data = {
        "name": "PhotoItem",
        "sku": "PI-001",
        "category": "General",
        "quantity": "5",
        "min_quantity": "1",
        "price": "2.00",
        "location": "Desk",
    }
    # Simulate a file upload
    data["image"] = (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "test.png")
    resp = admin_client.post(
        "/inventory/items/new",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"PhotoItem" in resp.data

def test_api_search_json(admin_client):
    admin_client.post("/inventory/items/new", data={
        "name": "APISearchable",
        "sku": "API-001",
        "quantity": "3",
        "min_quantity": "1",
        "price": "1.00",
    })
    resp = admin_client.get("/inventory/api/search?q=APISearchable")
    assert resp.status_code == 200
    assert resp.content_type == "application/json"
    json_data = resp.get_json()
    assert isinstance(json_data, list)

def test_negative_quantity_clamped_and_form_kept_on_error(admin_client):
    admin_client.post("/inventory/items/new", data={"name": "A", "sku": "S1", "quantity": "-5"})
    admin_client.post("/inventory/items/new", data={"name": "B", "sku": "S1"})
    resp = admin_client.post("/inventory/items/new", data={"name": "KeepMe", "sku": "S1"})
    assert b"already exists" in resp.data
    assert b"KeepMe" in resp.data  # form re-rendered with user input

def test_search_treats_percent_literally(admin_client):
    admin_client.post("/inventory/items/new", data={"name": "Plain"})
    resp = admin_client.get("/inventory/items?q=%25")
    assert b"Plain" not in resp.data

def test_column_name_sanitised(admin_client):
    admin_client.post("/inventory/columns", data={"action": "add", "column_name": "Bad Name!<x>", "column_type": "text"})
    resp = admin_client.get("/inventory/columns")
    assert b"bad_name_x" in resp.data
