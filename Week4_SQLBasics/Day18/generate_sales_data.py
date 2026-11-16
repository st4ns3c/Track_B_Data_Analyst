"""
Nairobi wholesale distributor: sample sales database for Python reports
----------------------------------------------------------------------
Build plan
  Problem : the operations team wants a Python script that can query the
            orders database from any machine for the Monday report.
  Input   : none. This script makes the data.
  Output  : data/sales.db with one `orders` table and 28 orders placed
            between August and October 2026.

This is a self-contained copy of the Day 16 orders data, so Day 18 runs
without needing the Day 16 folder or its generated database.

Usage:
    python generate_sales_data.py

Requirements:
    Python 3.10 or later. No third-party packages.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "sales.db"

# order_id, customer_name, county, product, quantity, unit_price,
# order_date, status. Every value is fixed, so every run is reproducible.
ORDERS = [
    (2001, "Kamau Stores", "Nairobi", "Maize Flour 2kg", 50, 120, "2026-08-03", "delivered"),
    (2002, "Otieno Wholesale", "Kisumu", "Cooking Oil 5L", 30, 850, "2026-08-05", "delivered"),
    (2003, "Njoroge Supplies", "Nakuru", "Sugar 1kg", 200, 115, "2026-08-07", "pending"),
    (2004, "Hassan Traders", "Mombasa", "Rice 25kg", 40, 3200, "2026-08-10", "delivered"),
    (2005, "Waweru Ltd", "Nairobi", "Maize Flour 2kg", 80, 120, "2026-08-12", "pending"),
    (2006, "Owino Trading", "Kisumu", "Sugar 1kg", 150, 115, "2026-08-14", "delivered"),
    (2007, "Karanja Mart", "Mombasa", "Cooking Oil 5L", 20, 850, "2026-08-17", "pending"),
    (2008, "Kiprono Stores", "Eldoret", "Rice 25kg", 15, 3200, "2026-08-19", "delivered"),
    (2009, "Ochieng Supplies", "Kisumu", "Maize Flour 2kg", 100, 120, "2026-08-21", "delivered"),
    (2010, "Mutua Wholesale", "Machakos", "Cooking Oil 5L", 25, 850, "2026-08-24", "pending"),
    (2011, "Achieng Retail", "Kisumu", "Soap 1kg", 40, 210, "2026-08-26", "delivered"),
    (2012, "Mwangi Mini Mart", "Thika", "Wheat Flour 2kg", 40, 160, "2026-08-28", "delivered"),
    (2013, "Chebet Distributors", "Eldoret", "Sugar 1kg", 400, 115, "2026-09-02", "delivered"),
    (2014, "Yusuf Wholesale", "Mombasa", "Rice 25kg", 20, 3200, "2026-09-04", "pending"),
    (2015, "Njeri Enterprises", "Nyeri", "Maize Flour 2kg", 140, 120, "2026-09-07", "delivered"),
    (2016, "Kamau Stores", "Nairobi", "Cooking Oil 5L", 35, 850, "2026-09-09", "delivered"),
    (2017, "Otieno Wholesale", "Kisumu", "Rice 25kg", 12, 3200, "2026-09-11", "delivered"),
    (2018, "Hassan Traders", "Mombasa", "Sugar 1kg", 300, 115, "2026-09-15", "delivered"),
    (2019, "Njoroge Supplies", "Nakuru", "Wheat Flour 2kg", 60, 160, "2026-09-18", "delivered"),
    (2020, "Waweru Ltd", "Nairobi", "Soap 1kg", 60, 210, "2026-09-22", "pending"),
    (2021, "Karanja Mart", "Mombasa", "Cooking Oil 5L", 80, 850, "2026-09-25", "pending"),
    (2022, "Kiprono Stores", "Eldoret", "Maize Flour 2kg", 220, 120, "2026-09-29", "delivered"),
    (2023, "Ochieng Supplies", "Kisumu", "Sugar 1kg", 500, 115, "2026-10-02", "pending"),
    (2024, "Mutua Wholesale", "Machakos", "Rice 25kg", 45, 3200, "2026-10-06", "delivered"),
    (2025, "Achieng Retail", "Kisumu", "Wheat Flour 2kg", 30, 160, "2026-10-09", "delivered"),
    (2026, "Mwangi Mini Mart", "Thika", "Soap 1kg", 40, 210, "2026-10-13", "delivered"),
    (2027, "Njeri Enterprises", "Nyeri", "Cooking Oil 5L", 28, 850, "2026-10-16", "delivered"),
    (2028, "Chebet Distributors", "Eldoret", "Rice 25kg", 18, 3200, "2026-10-20", "pending"),
]

SCHEMA = """
CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    county       TEXT NOT NULL,
    product      TEXT NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   REAL NOT NULL CHECK (unit_price > 0),
    order_date   TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('delivered', 'pending'))
)
"""


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute(SCHEMA)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ORDERS)
        conn.commit()

        count, revenue = conn.execute(
            "SELECT COUNT(*), SUM(quantity * unit_price) FROM orders"
        ).fetchone()
        first, last = conn.execute(
            "SELECT MIN(order_date), MAX(order_date) FROM orders"
        ).fetchone()

    print(f"Wrote {count} orders to {DB_PATH}")
    print(f"Period: {first} to {last}")
    print(f"Total value: KES {revenue:,.0f}")


if __name__ == "__main__":
    main()
