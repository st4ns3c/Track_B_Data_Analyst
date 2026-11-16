"""
Nairobi wholesale distributor: customers and orders
---------------------------------------------------
Build plan
  Problem : the sales manager wants to know which customers drive revenue and
            whether the best customers cluster in one county. The answer needs
            two tables, joined on customer_id.
  Input   : none. This script makes the data.
  Output  : data/distributor.db, with a `customers` table (14 rows) and an
            `orders` table (44 rows). One customer has never ordered, which
            makes the LEFT JOIN lesson visible.

Usage:
    python generate_data.py

Requirements:
    Python 3.10 or later. No third-party packages.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "distributor.db"

CUSTOMERS = [
    (1, "Kamau Stores", "Nairobi", "silver"),
    (2, "Otieno Wholesale", "Kisumu", "gold"),
    (3, "Hassan Traders", "Mombasa", "gold"),
    (4, "Kiprono Stores", "Eldoret", "bronze"),
    (5, "Ochieng Supplies", "Kisumu", "silver"),
    (6, "Baraka Distributors", "Nairobi", "gold"),
    (7, "Waweru Ltd", "Nairobi", "bronze"),
    (8, "Njoroge Supplies", "Nakuru", "silver"),
    (9, "Mutua Wholesale", "Machakos", "gold"),
    (10, "Chebet Distributors", "Eldoret", "gold"),
    (11, "Njeri Enterprises", "Nyeri", "bronze"),
    (12, "Achieng Retail", "Kisumu", "bronze"),
    (13, "Karanja Mart", "Mombasa", "silver"),
    (14, "Mwangi Mini Mart", "Thika", "silver"),
]

# order_id, customer_id, product, quantity, unit_price, order_date, status.
# The rows are fixed, so every run produces the same totals and the same six
# customers with more than three orders. Customer 6 is deliberately dormant.
ORDERS = [
    (3001, 1, "Maize Flour 2kg", 60, 120, "2026-08-03", "delivered"),
    (3002, 2, "Rice 25kg", 25, 3200, "2026-08-04", "delivered"),
    (3003, 3, "Rice 25kg", 40, 3200, "2026-08-05", "delivered"),
    (3004, 4, "Rice 25kg", 15, 3200, "2026-08-06", "delivered"),
    (3005, 5, "Sugar 1kg", 400, 115, "2026-08-07", "delivered"),
    (3006, 7, "Maize Flour 2kg", 100, 120, "2026-08-10", "delivered"),
    (3007, 8, "Wheat Flour 2kg", 140, 160, "2026-08-11", "delivered"),
    (3008, 9, "Rice 25kg", 30, 3200, "2026-08-12", "delivered"),
    (3009, 10, "Sugar 1kg", 400, 115, "2026-08-13", "delivered"),
    (3010, 11, "Wheat Flour 2kg", 60, 160, "2026-08-14", "delivered"),
    (3011, 12, "Soap 1kg", 60, 210, "2026-08-17", "delivered"),
    (3012, 13, "Cooking Oil 5L", 50, 850, "2026-08-18", "delivered"),
    (3013, 14, "Wheat Flour 2kg", 90, 160, "2026-08-19", "delivered"),
    (3014, 1, "Cooking Oil 5L", 20, 850, "2026-08-20", "delivered"),
    (3015, 2, "Sugar 1kg", 300, 115, "2026-08-21", "delivered"),
    (3016, 3, "Sugar 1kg", 350, 115, "2026-08-24", "delivered"),
    (3017, 5, "Cooking Oil 5L", 25, 850, "2026-08-25", "delivered"),
    (3018, 9, "Cooking Oil 5L", 35, 850, "2026-08-26", "delivered"),
    (3019, 10, "Rice 25kg", 18, 3200, "2026-08-27", "delivered"),
    (3020, 4, "Maize Flour 2kg", 180, 120, "2026-08-28", "delivered"),
    (3021, 7, "Sugar 1kg", 180, 115, "2026-08-31", "delivered"),
    (3022, 8, "Sugar 1kg", 300, 115, "2026-09-01", "delivered"),
    (3023, 12, "Maize Flour 2kg", 80, 120, "2026-09-02", "delivered"),
    (3024, 1, "Sugar 1kg", 250, 115, "2026-09-03", "delivered"),
    (3025, 2, "Cooking Oil 5L", 40, 850, "2026-09-04", "delivered"),
    (3026, 3, "Cooking Oil 5L", 30, 850, "2026-09-07", "pending"),
    (3027, 5, "Rice 25kg", 12, 3200, "2026-09-08", "delivered"),
    (3028, 9, "Sugar 1kg", 500, 115, "2026-09-09", "pending"),
    (3029, 10, "Cooking Oil 5L", 60, 850, "2026-09-10", "pending"),
    (3030, 11, "Cooking Oil 5L", 28, 850, "2026-09-11", "delivered"),
    (3031, 12, "Sugar 1kg", 150, 115, "2026-09-14", "delivered"),
    (3032, 13, "Sugar 1kg", 200, 115, "2026-09-15", "delivered"),
    (3033, 4, "Sugar 1kg", 200, 115, "2026-09-16", "pending"),
    (3034, 7, "Soap 1kg", 100, 210, "2026-09-17", "delivered"),
    (3035, 1, "Rice 25kg", 10, 3200, "2026-09-18", "pending"),
    (3036, 2, "Maize Flour 2kg", 150, 120, "2026-09-21", "delivered"),
    (3037, 3, "Maize Flour 2kg", 90, 120, "2026-09-22", "delivered"),
    (3038, 5, "Maize Flour 2kg", 120, 120, "2026-09-23", "delivered"),
    (3039, 9, "Maize Flour 2kg", 200, 120, "2026-09-24", "delivered"),
    (3040, 10, "Maize Flour 2kg", 220, 120, "2026-09-25", "delivered"),
    (3041, 13, "Maize Flour 2kg", 140, 120, "2026-09-28", "delivered"),
    (3042, 14, "Soap 1kg", 40, 210, "2026-09-29", "delivered"),
    (3043, 2, "Wheat Flour 2kg", 80, 160, "2026-09-30", "delivered"),
    (3044, 10, "Sugar 1kg", 250, 115, "2026-10-01", "delivered"),
]

CUSTOMERS_SCHEMA = """
CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    county       TEXT NOT NULL,
    account_tier TEXT NOT NULL CHECK (account_tier IN ('bronze', 'silver', 'gold'))
)
"""

ORDERS_SCHEMA = """
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product     TEXT NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  REAL NOT NULL CHECK (unit_price > 0),
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('delivered', 'pending'))
)
"""


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        # Drop the child table first so the foreign key never blocks a rebuild.
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("DROP TABLE IF EXISTS customers")
        conn.execute(CUSTOMERS_SCHEMA)
        conn.execute(ORDERS_SCHEMA)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", ORDERS)
        conn.commit()

        customers, orders, revenue = conn.execute(
            "SELECT (SELECT COUNT(*) FROM customers), COUNT(*), "
            "SUM(quantity * unit_price) FROM orders"
        ).fetchone()
        first, last = conn.execute(
            "SELECT MIN(order_date), MAX(order_date) FROM orders"
        ).fetchone()
        dormant = conn.execute(
            "SELECT customer_name FROM customers c "
            "LEFT JOIN orders o ON c.customer_id = o.customer_id "
            "WHERE o.order_id IS NULL"
        ).fetchall()

    print(f"Wrote {customers} customers and {orders} orders to {DB_PATH}")
    print(f"Period: {first} to {last}")
    print(f"Total value: KES {revenue:,.0f}")
    print(f"Customers with no orders: {', '.join(name for (name,) in dormant)}")


if __name__ == "__main__":
    main()
