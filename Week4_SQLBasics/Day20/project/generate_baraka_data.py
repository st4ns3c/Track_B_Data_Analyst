"""
Baraka Distributors: Q1 2024 sales database
-------------------------------------------
Build plan
  Problem : Baraka Distributors sells five dry-goods lines to shops in five
            counties. The owner wants a first-quarter review from the sales
            database rather than from the order book.
  Input   : none. This script makes the data.
  Output  : data/baraka_distributors.db with the `sales` table from the
            lesson (id, date, product, county, quantity, unit_price) holding
            every order from 2 January to 30 March 2024, plus indexes on
            date and county.

The seed is fixed (2024), so every run writes the same orders. Nairobi and
Kisumu are the established markets; Mombasa was opened late in 2023 and gets
few orders, which is the gap the analysis is meant to find.

Usage:
    python generate_baraka_data.py

Requirements:
    pip install numpy
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "baraka_distributors.db"

SEED = 2024
START = date(2024, 1, 2)
END = date(2024, 3, 30)

# Product: (price per bale or carton in KES, typical quantity per order,
# share of orders). Prices are the lesson's, plus sugar.
PRODUCTS = {
    "Rice": (4500, 95, 0.24),
    "Maize Flour": (2800, 110, 0.30),
    "Wheat Flour": (3200, 70, 0.16),
    "Cooking Oil": (1800, 60, 0.14),
    "Sugar": (3600, 50, 0.16),
}

# County: expected orders per working day. Mombasa is the late starter.
COUNTIES = {
    "Nairobi": 0.95,
    "Kisumu": 0.70,
    "Nakuru": 0.40,
    "Eldoret": 0.30,
    "Mombasa": 0.15,
}

# Same table as the lesson, with constraints so a bad row is refused at the door.
SCHEMA = """
CREATE TABLE sales (
    id         INTEGER PRIMARY KEY,
    date       TEXT NOT NULL,
    product    TEXT NOT NULL,
    county     TEXT NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price > 0)
)
"""


def working_days(start, end):
    """Monday to Saturday; the depot is closed on Sunday."""
    day = start
    while day <= end:
        if day.weekday() < 6:
            yield day
        day += timedelta(days=1)


def build_rows(rng):
    days = list(working_days(START, END))
    product_names = list(PRODUCTS)
    product_weights = [p[2] for p in PRODUCTS.values()]

    rows = []
    for i, day in enumerate(days):
        # Shops restock slowly after the December holidays, so January is the
        # quietest month and orders build into March.
        season = 0.85 + 0.30 * i / (len(days) - 1)
        for county, rate in COUNTIES.items():
            for _ in range(rng.poisson(rate * season)):
                product = rng.choice(product_names, p=product_weights)
                price, base_qty, _ = PRODUCTS[product]
                quantity = max(5, int(round(base_qty * rng.lognormal(0, 0.3) / 5) * 5))
                rows.append((day.isoformat(), str(product), county, quantity, price))

    rows.sort(key=lambda r: r[0])
    return rows


def main():
    rng = np.random.default_rng(SEED)
    rows = build_rows(rng)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(SCHEMA)
        conn.executemany(
            "INSERT INTO sales (date, product, county, quantity, unit_price) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        # Every question in the report groups by county or by month.
        conn.execute("CREATE INDEX idx_sales_county ON sales(county)")
        conn.execute("CREATE INDEX idx_sales_date ON sales(date)")
        conn.commit()

        count, first, last, revenue = conn.execute(
            "SELECT COUNT(*), MIN(date), MAX(date), SUM(quantity * unit_price) "
            "FROM sales"
        ).fetchone()

    print(f"Wrote {count} orders to {DB_PATH}")
    print(f"Period: {first} to {last}")
    print(f"Revenue: KES {revenue:,.0f}")


if __name__ == "__main__":
    main()
