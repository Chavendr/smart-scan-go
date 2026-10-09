import sqlite3
import os
from contextlib import closing

# Stored in your user folder (outside OneDrive) so syncing can't lock it
DB_NAME = os.path.join(os.path.expanduser("~"), "smartscan_shop.db")

def get_conn():
    return sqlite3.connect(DB_NAME, timeout=30)

def init_db():
    with closing(get_conn()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    items TEXT,
                    total INTEGER,
                    status TEXT,
                    signature TEXT,
                    used INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    password_hash TEXT
                )
            """)

def save_order(order_id, items, total, status, signature, used):
    with closing(get_conn()) as conn:
        with conn:
            conn.execute("""
                INSERT INTO orders (order_id, items, total, status, signature, used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, ",".join(items), total, status, signature, int(used)))

def _row_to_order(row):
    return {
        "order_id": row[0],
        "items": row[1].split(",") if row[1] else [],
        "total": row[2],
        "status": row[3],
        "signature": row[4],
        "used": bool(row[5])
    }

def get_order(order_id):
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    return _row_to_order(row) if row else None

def mark_order_used(order_id):
    with closing(get_conn()) as conn:
        with conn:
            conn.execute("UPDATE orders SET used = 1 WHERE order_id = ?", (order_id,))

def get_all_orders():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT * FROM orders").fetchall()
    return [_row_to_order(r) for r in rows]

# ---------- User accounts ----------

def add_user(name, email, password_hash):
    try:
        with closing(get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, password_hash)
                )
        return True
    except sqlite3.IntegrityError:
        return False

def get_user_by_email(email):
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2], "password_hash": row[3]}
    return None