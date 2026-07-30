import sqlite3

DB_NAME = "shop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            items TEXT,
            total INTEGER,
            status TEXT,
            signature TEXT,
            used INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_order(order_id, items, total, status, signature, used):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (order_id, items, total, status, signature, used)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, ",".join(items), total, status, signature, int(used)))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "order_id": row[0],
            "items": row[1].split(","),
            "total": row[2],
            "status": row[3],
            "signature": row[4],
            "used": bool(row[5])
        }
    return None

def mark_order_used(order_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET used = 1 WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

def get_all_orders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    rows = cursor.fetchall()
    conn.close()
    all_orders = []
    for row in rows:
        all_orders.append({
            "order_id": row[0],
            "items": row[1].split(","),
            "total": row[2],
            "status": row[3],
            "signature": row[4],
            "used": bool(row[5])
        })
    return all_orders