"""
Database abstraction layer.

Active driver  : aiosqlite  (async SQLite)
Future driver  : asyncpg    (async PostgreSQL) – commented out, ready to enable.
"""

import sqlite3
import json
import os
import aiosqlite

# =====================================================================

#  PostgreSQL async driver (uncomment when switching to PostgreSQL)

# =====================================================================

# import asyncpg

#
# class PostgreSQLDatabase:

#     """Async PostgreSQL wrapper using asyncpg with a connection pool."""

#
#     def __init__(self, dsn: str):

#         self.dsn = dsn

#         self.pool = None

#
#     async def connect(self):

#         self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=2, max_size=10)

#
#     async def close(self):

#         if self.pool:

#             await self.pool.close()

#
#     async def fetch_one(self, query: str, params: list | None = None):

#         async with self.pool.acquire() as conn:

#             row = await conn.fetchrow(query, *(params or []))

#             return dict(row) if row else None

#
#     async def fetch_all(self, query: str, params: list | None = None):

#         async with self.pool.acquire() as conn:

#             rows = await conn.fetch(query, *(params or []))

#             return [dict(r) for r in rows]

#
#     async def execute(self, query: str, params: list | None = None):

#         async with self.pool.acquire() as conn:

#             return await conn.execute(query, *(params or []))

#
#     async def execute_returning_id(self, query: str, params: list | None = None):

#         """PostgreSQL-specific: use RETURNING id."""

#         async with self.pool.acquire() as conn:

#             row = await conn.fetchrow(query, *(params or []))

#             return row["id"] if row else None

# =====================================================================

class SQLiteDatabase:
    """Async SQLite wrapper using aiosqlite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ── helpers ──────────────────────────────────────────────────────
    async def fetch_one(self, query: str, params: tuple | list | None = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple | list | None = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def execute(self, query: str, params: tuple | list | None = None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params or ())
            await db.commit()
            return cursor.lastrowid

    async def execute_many(self, query: str, params_list: list):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(query, params_list)
            await db.commit()

# ── Schema (SQLite) ─────────────────────────────────────────────────
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    UNIQUE NOT NULL,
    email           TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    role            TEXT    DEFAULT 'viewer',       -- 'admin' | 'viewer'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- PostgreSQL equivalent:
-- CREATE TABLE IF NOT EXISTS users (
--     id            SERIAL PRIMARY KEY,
--     username      VARCHAR(80) UNIQUE NOT NULL,
--     email         VARCHAR(120) UNIQUE NOT NULL,
--     password_hash VARCHAR(256) NOT NULL,
--     role          VARCHAR(10) DEFAULT 'viewer',
--     created_at    TIMESTAMPTZ DEFAULT NOW()
-- );

CREATE TABLE IF NOT EXISTS inventory_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
        description     TEXT    DEFAULT '',
    sku             TEXT    UNIQUE,
    category        TEXT    DEFAULT 'General',
    quantity         INTEGER DEFAULT 0,
    min_quantity     INTEGER DEFAULT 0,
    price           REAL    DEFAULT 0.0,
    location        TEXT    DEFAULT '',
    image_path      TEXT    DEFAULT '',
    custom_fields   TEXT    DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- PostgreSQL equivalent:
-- CREATE TABLE IF NOT EXISTS inventory_items (
--     id            SERIAL PRIMARY KEY,
--     name          VARCHAR(200) NOT NULL,
--     description   TEXT DEFAULT '',
--     sku           VARCHAR(100) UNIQUE,
--     category      VARCHAR(100) DEFAULT 'General',
--     quantity      INTEGER DEFAULT 0,
--     min_quantity  INTEGER DEFAULT 0,
--     price         NUMERIC(12,2) DEFAULT 0.0,
--     location      VARCHAR(200) DEFAULT '',
--     image_path    VARCHAR(500) DEFAULT '',
--     custom_fields JSONB DEFAULT '{}',
--     created_at    TIMESTAMPTZ DEFAULT NOW(),
--     updated_at    TIMESTAMPTZ DEFAULT NOW()
-- );

CREATE TABLE IF NOT EXISTS custom_columns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    column_name     TEXT    UNIQUE NOT NULL,
    column_type     TEXT    DEFAULT 'text',   -- text | number | date
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- PostgreSQL equivalent:
-- CREATE TABLE IF NOT EXISTS custom_columns (
--     id           SERIAL PRIMARY KEY,
--     column_name  VARCHAR(100) UNIQUE NOT NULL,
--     column_type  VARCHAR(20) DEFAULT 'text',
--     created_at   TIMESTAMPTZ DEFAULT NOW()
-- );
"""

def init_db_sync(db_path: str):
    """Run once at startup to guarantee tables exist (synchronous)."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SQLITE_SCHEMA)
    conn.close()