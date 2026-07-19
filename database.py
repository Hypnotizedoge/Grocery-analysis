"""
database.py — SQLite database layer for the Grocery Price Tracker.

Tables:
  - stores: grocery store master list
  - products: product catalog linked to stores
  - price_history: price entries per product per date
"""

import sqlite3
import os
from datetime import date, datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grocery_tracker.db")

# ─── Default seed data ────────────────────────────────────────────────────────

DEFAULT_STORES = [
    "SM Supermarket",
    "Robinsons Supermarket",
    "Puregold",
    "Landers",
    "S&R Membership Shopping",
    "Metro Mart",
    "Walter Mart",
    "Shopwise",
    "Rustans",
    "Landmark Supermarket",
]

DEFAULT_CATEGORIES = [
    "Beverages",
    "Bread & Bakery",
    "Canned Goods",
    "Condiments & Sauces",
    "Dairy",
    "Frozen",
    "Fruits & Vegetables",
    "Grains & Pasta",
    "Meat & Seafood",
    "Snacks",
    "Household",
    "Personal Care",
    "Baby & Kids",
    "Pet Supplies",
    "Others",
]

# ─── Database initialization ──────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed default data if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS products (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL,
                category        TEXT    NOT NULL,
                item_name       TEXT    NOT NULL,
                brand           TEXT    NOT NULL DEFAULT '',
                weight_volume   TEXT    NOT NULL DEFAULT '',
                unit            TEXT    NOT NULL DEFAULT '',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (store_id) REFERENCES stores(id),
                UNIQUE(store_id, item_name, brand, weight_volume)
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id      INTEGER NOT NULL,
                price           REAL    NOT NULL,
                date_recorded   TEXT    NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id),
                UNIQUE(product_id, date_recorded)
            );
        """)

        # Seed default stores
        for store_name in DEFAULT_STORES:
            conn.execute(
                "INSERT OR IGNORE INTO stores (name) VALUES (?)", (store_name,)
            )

        conn.commit()


# ─── Store CRUD ───────────────────────────────────────────────────────────────

def get_stores() -> list[dict]:
    """Return all stores as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM stores ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def add_store(name: str) -> int:
    """Add a new store. Returns the new store id."""
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO stores (name) VALUES (?)", (name.strip(),))
        conn.commit()
        return cursor.lastrowid


# ─── Product CRUD ─────────────────────────────────────────────────────────────

def add_product(
    store_id: int,
    category: str,
    item_name: str,
    brand: str = "",
    weight_volume: str = "",
    unit: str = "",
) -> int:
    """Add a product. Returns the product id (existing or new)."""
    with get_connection() as conn:
        # Check if this exact product already exists
        existing = conn.execute(
            """SELECT id FROM products
               WHERE store_id = ? AND item_name = ? AND brand = ? AND weight_volume = ?""",
            (store_id, item_name.strip(), brand.strip(), weight_volume.strip()),
        ).fetchone()

        if existing:
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO products (store_id, category, item_name, brand, weight_volume, unit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                store_id,
                category.strip(),
                item_name.strip(),
                brand.strip(),
                weight_volume.strip(),
                unit.strip(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_products(
    store_id: int,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Get products for a store, optionally filtered."""
    query = """
        SELECT p.id, p.store_id, p.category, p.item_name, p.brand,
               p.weight_volume, p.unit, p.created_at,
               ph.price AS latest_price, ph.date_recorded AS last_updated
        FROM products p
        LEFT JOIN price_history ph ON ph.id = (
            SELECT ph2.id FROM price_history ph2
            WHERE ph2.product_id = p.id
            ORDER BY ph2.date_recorded DESC LIMIT 1
        )
        WHERE p.store_id = ?
    """
    params: list = [store_id]

    if category:
        query += " AND p.category = ?"
        params.append(category)

    if brand:
        query += " AND p.brand = ?"
        params.append(brand)

    if search:
        query += " AND (p.item_name LIKE ? OR p.brand LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY p.category, p.item_name"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_product_by_id(product_id: int) -> Optional[dict]:
    """Get a single product by id."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT p.*, ph.price AS latest_price, ph.date_recorded AS last_updated
               FROM products p
               LEFT JOIN price_history ph ON ph.id = (
                   SELECT ph2.id FROM price_history ph2
                   WHERE ph2.product_id = p.id
                   ORDER BY ph2.date_recorded DESC LIMIT 1
               )
               WHERE p.id = ?""",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


# ─── Price History ────────────────────────────────────────────────────────────

def add_price(product_id: int, price: float, date_recorded: Optional[str] = None) -> int:
    """Add a price entry. Defaults to today's date. Upserts if same date exists."""
    if date_recorded is None:
        date_recorded = date.today().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO price_history (product_id, price, date_recorded)
               VALUES (?, ?, ?)
               ON CONFLICT(product_id, date_recorded)
               DO UPDATE SET price = excluded.price""",
            (product_id, price, date_recorded),
        )
        conn.commit()
        return cursor.lastrowid


def get_price_history(product_id: int) -> list[dict]:
    """Get all price history for a product, ordered by date."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT price, date_recorded
               FROM price_history
               WHERE product_id = ?
               ORDER BY date_recorded ASC""",
            (product_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_price_today(product_id: int, price: float):
    """Upsert price for today."""
    add_price(product_id, price, date.today().isoformat())


# ─── Filter helpers ───────────────────────────────────────────────────────────

def get_categories(store_id: Optional[int] = None) -> list[str]:
    """Get distinct categories, optionally for a specific store."""
    with get_connection() as conn:
        if store_id:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products WHERE store_id = ? ORDER BY category",
                (store_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products ORDER BY category"
            ).fetchall()
        return [r["category"] for r in rows]


def get_brands(store_id: Optional[int] = None, category: Optional[str] = None) -> list[str]:
    """Get distinct brands, optionally filtered by store and/or category."""
    query = "SELECT DISTINCT brand FROM products WHERE brand != ''"
    params: list = []

    if store_id:
        query += " AND store_id = ?"
        params.append(store_id)

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY brand"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [r["brand"] for r in rows]


def delete_product(product_id: int):
    """Delete a product and its price history."""
    with get_connection() as conn:
        conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def get_product_count_by_store(store_id: int) -> int:
    """Get total product count for a store."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE store_id = ?", (store_id,)
        ).fetchone()
        return row["cnt"]
