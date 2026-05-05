# InventoryPro - Modern Inventory Management System

InventoryPro is a powerful, lightweight, and modern inventory management application built with **Async Flask**, **SQLite (aiosqlite)**, and **Bootstrap 5**. It features robust Role-Based Access Control (RBAC), dynamic custom columns, and a polished dark-mode-ready interface.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9 or higher
- Pip (Python package manager)

### 2. Setup Virtual Environment

#### **On Windows:**
```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

#### **On macOS / Linux:**
```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requiremtns.txt
```

### 4. Configuration
1. Copy the example configuration file:
   ```bash
   cp config/secrets.example.ini config/secrets.ini
   ```
2. Edit `config/secrets.ini` to set your `secret_key` and other preferences.

### 5. Run the Application
```bash
python run.py
```
The application will be available at `http://localhost:5000`.

---

## 🔐 Authentication & Roles

### Default Admin Credentials
For initial setup, the **very first user** registered in the system is automatically granted the **Admin** role. 

<<<<<<< HEAD
**Recommended Initial Admin:**
- **Username:** `admin`
- **Password:** `admin123`

*Note: Public registration is disabled once the first admin is created. All subsequent users must be created by an Admin.*

### Role Definitions:
1.  **Admin**:
    - Full access to User Management (Create/Edit/Delete users and assign roles).
    - Full access to Inventory (CRUD operations).
    - Ability to manage **Custom Columns** (Dynamic fields).
2.  **Editor**:
    - Full CRUD access to **Inventory** (Add/Edit/Delete items).
    - Read-only access to system settings.
3.  **Viewer**:
    - Read-only access to the Dashboard and Inventory list.
    - No permission to modify any data.

---

## 🛠 Features in Detail

### 📊 Dashboard
- **Quick Stats**: Real-time count of total items and critical low-stock alerts.
- **Stock Alerts**: Automatic listing of items that fall below their defined `min_quantity`.
- **Role Badge**: High-visibility indicator of your current access level.

### 📦 Inventory Management
- **Item Creation**: Add items with Name, SKU, Category, Price, Quantity, and Location.
- **Image Uploads**: Attach product images to inventory items.
- **Dynamic Search**: Search across all columns or filter by specific fields (SKU, Name, etc.).
- **AJAX Search**: Fast, responsive search interface.

### 🧩 Custom Columns
- **Flexibility**: Admins can add new fields to the inventory (e.g., "Serial Number", "Expiry Date") without changing the code.
- **Field Types**: Supports multiple column types like text, number, and date.

### 👥 User Management (Admin Only)
- **Centralized Control**: Admins can create new team members and assign them one of the three roles.
- **Account Security**: Secure password hashing using Werkzeug.
- **Self-Protection**: The system prevents admins from deleting their own accounts to avoid lockouts.

---

## 🌓 UI & Aesthetics
- **Dark Mode**: Toggle between light and dark themes with a single click (persistence via LocalStorage).
- **Responsive Design**: Fully functional on mobile, tablet, and desktop.
- **Hover Effects**: Polished interactive elements and high-contrast row highlighting.

---

## 🐘 Moving to PostgreSQL
The system is designed to be database-agnostic. To switch from SQLite to PostgreSQL in the future:

1.  **Update Config**: In `config/secrets.ini`, change `type = sqlite` to `type = postgresql` and uncomment the PostgreSQL connection details.
2.  **Enable Driver**: In `app/database.py`, uncomment `import asyncpg` and the `PostgreSQLDatabase` class.
3.  **Update Factory**: In `app/__init__.py`, uncomment the PostgreSQL initialization logic.
4.  **Install Requirements**: Add `asyncpg` to your `requiremtns.txt`.

---

## 📁 Project Structure
- `app/`: Core application logic (Routes, Models, Database).
- `app/templates/`: Jinja2 HTML templates.
- `app/static/`: CSS, JS, and uploaded images.
- `config/`: Configuration files and environment secrets.
- `data/`: Local SQLite database storage.
- `run.py`: Application entry point.
=======
## License
MIT License
>>>>>>> f06b46a0768405137930e16357a7e540b395c197
