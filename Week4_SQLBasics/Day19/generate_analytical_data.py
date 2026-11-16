"""
Nairobi wholesale distributor: analytical query data
----------------------------------------------------
Build plan
  Problem : the CFO wants trend analysis, not just totals. The board asked
            three questions that the weekly order report cannot answer:
            the status mix by county, which customers are growing month on
            month, and how revenue accumulates through the quarter.
  Input   : none. This script makes the data.
  Output  : data/analytics.db with a `customers` table (12 rows) and an
            `orders` table (41 rows) spanning August to October 2026, plus
            indexes on customers(county) and orders(customer_id) for the
            query-plan demonstration.

The rows are fixed, so every run reproduces the same percentages, monthly
values and running total. Two customers grow in both September and October,
and five cancelled orders give the status report something to show.

Usage:
    python generate_analytical_data.py

Requirements:
    Python 3.10 or later. No third-party packages.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "analytics.db"

CUSTOMERS = [
    (1, "Kamau Stores", "Nairobi", "silver"),
    (2, "Otieno Wholesale", "Kisumu", "gold"),
    (3, "Hassan Traders", "Mombasa", "gold"),
    (4, "Kiprono Stores", "Eldoret", "bronze"),
    (5, "Ochieng Supplies", "Kisumu", "silver"),
    (6, "Waweru Ltd", "Nairobi", "bronze"),
    (7, "Njoroge Supplies", "Nakuru", "silver"),
    (8, "Mutua Wholesale", "Machakos", "gold"),
    (9, "Chebet Distributors", "Eldoret", "gold"),
    (10, "Njeri Enterprises", "Nyeri", "bronze"),
    (11, "Achieng Retail", "Kisumu", "bronze"),
    (12, "Mwangi Mini Mart", "Thika", "silver"),
]

# order_id, customer_id, product, quantity, unit_price, order_date, status.
# The monthly values are deliberately shaped: Kamau Stores and Njeri
# Enterprises rise in both September and October, while most other accounts
# rise once and then fall. Cancelled rows sit beside a live order in the same
# month, so excluding them never hides a customer from the month-on-month
# comparison.
ORDERS = [
    (4001, 1, "Maize Flour 2kg", 50, 120, "2026-08-03", "completed"),
    (4002, 2, "Rice 25kg", 25, 3200, "2026-08-05", "completed"),
    (4003, 3, "Rice 25kg", 40, 3200, "2026-08-07", "completed"),
    (4004, 6, "Maize Flour 2kg", 100, 120, "2026-08-10", "completed"),
    (4005, 7, "Wheat Flour 2kg", 140, 160, "2026-08-11", "completed"),
    (4006, 1, "Cooking Oil 5L", 20, 850, "2026-08-12", "completed"),
    (4007, 4, "Rice 25kg", 15, 3200, "2026-08-14", "completed"),
    (4008, 8, "Rice 25kg", 30, 3200, "2026-08-17", "completed"),
    (4009, 9, "Sugar 1kg", 400, 115, "2026-08-18", "completed"),
    (4010, 10, "Wheat Flour 2kg", 60, 160, "2026-08-20", "completed"),
    (4011, 5, "Sugar 1kg", 400, 115, "2026-08-21", "completed"),
    (4012, 1, "Maize Flour 2kg", 60, 120, "2026-09-04", "pending"),
    (4013, 6, "Sugar 1kg", 180, 115, "2026-09-08", "completed"),
    (4014, 2, "Rice 25kg", 30, 3200, "2026-09-10", "completed"),
    (4015, 3, "Rice 25kg", 35, 3200, "2026-09-12", "completed"),
    (4016, 1, "Cooking Oil 5L", 25, 850, "2026-09-15", "completed"),
    (4017, 4, "Rice 25kg", 10, 3200, "2026-09-16", "completed"),
    (4018, 5, "Sugar 1kg", 300, 115, "2026-09-18", "pending"),
    (4019, 7, "Sugar 1kg", 300, 115, "2026-09-19", "completed"),
    (4020, 9, "Sugar 1kg", 250, 115, "2026-09-22", "pending"),
    (4021, 8, "Cooking Oil 5L", 35, 850, "2026-09-24", "completed"),
    (4022, 11, "Soap 1kg", 60, 210, "2026-09-26", "completed"),
    (4023, 10, "Cooking Oil 5L", 28, 850, "2026-09-28", "completed"),
    (4024, 6, "Sugar 1kg", 100, 115, "2026-09-29", "cancelled"),
    (4025, 3, "Soap 1kg", 60, 210, "2026-09-30", "cancelled"),
    (4026, 1, "Maize Flour 2kg", 80, 120, "2026-10-02", "completed"),
    (4027, 6, "Sugar 1kg", 150, 115, "2026-10-06", "completed"),
    (4028, 2, "Rice 25kg", 20, 3200, "2026-10-08", "pending"),
    (4029, 3, "Rice 25kg", 45, 3200, "2026-10-09", "pending"),
    (4030, 4, "Rice 25kg", 12, 3200, "2026-10-12", "completed"),
    (4031, 7, "Sugar 1kg", 200, 115, "2026-10-13", "pending"),
    (4032, 1, "Cooking Oil 5L", 30, 850, "2026-10-14", "pending"),
    (4033, 9, "Sugar 1kg", 300, 115, "2026-10-16", "completed"),
    (4034, 8, "Rice 25kg", 45, 3200, "2026-10-18", "pending"),
    (4035, 5, "Sugar 1kg", 500, 115, "2026-10-20", "completed"),
    (4036, 10, "Cooking Oil 5L", 35, 850, "2026-10-21", "completed"),
    (4037, 11, "Maize Flour 2kg", 80, 120, "2026-10-22", "completed"),
    (4038, 5, "Soap 1kg", 40, 210, "2026-10-24", "cancelled"),
    (4039, 12, "Soap 1kg", 40, 210, "2026-10-26", "pending"),
    (4040, 8, "Maize Flour 2kg", 20, 120, "2026-10-27", "cancelled"),
    (4041, 9, "Wheat Flour 2kg", 60, 160, "2026-10-28", "cancelled"),
]

CUSTOMERS_SCHEMA = """
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    county        TEXT NOT NULL,
    account_tier  TEXT NOT NULL CHECK (account_tier IN ('bronze', 'silver', 'gold'))
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
    status      TEXT NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled'))
)
"""

# County lives on the customers table in this schema, so that is the filter
# the plan check targets. The join key gets its own index for the same reason:
# it is the column used to connect the two tables on every report.
PLAN_QUERY = "SELECT customer_id, customer_name FROM customers WHERE county = 'Mombasa'"


def plan(conn):
    return [row[3] for row in conn.execute(f"EXPLAIN QUERY PLAN {PLAN_QUERY}")]


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

        before = plan(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_county "
                     "ON customers(county)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer "
                     "ON orders(customer_id)")
        after = plan(conn)

        customers, orders = conn.execute(
            "SELECT (SELECT COUNT(*) FROM customers), COUNT(*) FROM orders"
        ).fetchone()
        completed, pending, cancelled = conn.execute(
            "SELECT SUM(status = 'completed'), SUM(status = 'pending'), "
            "SUM(status = 'cancelled') FROM orders"
        ).fetchone()
        revenue = conn.execute(
            "SELECT SUM(quantity * unit_price) FROM orders "
            "WHERE status <> 'cancelled'"
        ).fetchone()[0]
        first, last = conn.execute(
            "SELECT MIN(order_date), MAX(order_date) FROM orders"
        ).fetchone()

    print(f"Wrote {customers} customers and {orders} orders to {DB_PATH}")
    print(f"Period: {first} to {last}")
    print(f"Status mix: {completed} completed, {pending} pending, {cancelled} cancelled")
    print(f"Revenue from non-cancelled orders: KES {revenue:,.0f}")
    print(f"Plan before index: {before[0]}")
    print(f"Plan after index:  {after[0]}")


if __name__ == "__main__":
    main()
