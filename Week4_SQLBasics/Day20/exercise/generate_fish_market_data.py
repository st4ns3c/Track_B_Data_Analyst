"""
Kisumu fish market: first three months of digital sales
-------------------------------------------------------
Build plan
  Problem : a Kisumu fish market association moved its vendors from paper
            books to digital records in August 2026. A county government
            sponsor wants a report on the first three months.
  Input   : none. This script makes the data.
  Output  : data/fish_market.db with one `sales` table: vendor, fish type,
            kg sold, price per kg, date and buyer type (retail or wholesale),
            for every trading day (Monday to Saturday) from 3 August to
            31 October 2026, plus an index on the sale date.

The seed is fixed (20), so every run writes the same rows. Wholesale buyers
get a lower price per kg for buying in bulk, and volumes rise gently through
the quarter as more vendors start using the digital book.

Usage:
    python generate_fish_market_data.py

Requirements:
    pip install numpy
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "fish_market.db"

SEED = 20
START = date(2026, 8, 3)
END = date(2026, 10, 31)

# Vendor name and how busy the stall is (relative chance of a sale on a day).
VENDORS = {
    "Akinyi Fish Stall": 1.6,
    "Otieno & Sons": 1.4,
    "Mama Adhiambo": 1.2,
    "Ouma Lakeside Traders": 1.0,
    "Awino Fresh Fish": 0.9,
    "Onyango Omena Supplies": 0.8,
    "Atieno Smoked Fish": 0.6,
    "Owino Catch": 0.5,
}

# Fish type: (typical retail price per kg in KES, typical retail kg per sale).
FISH = {
    "Tilapia": (420, 12),
    "Nile Perch": (380, 18),
    "Omena": (180, 25),
    "Catfish": (320, 10),
}

# Wholesale buyers (hotels, schools, resellers) pay less per kg but buy more.
WHOLESALE_DISCOUNT = 0.82
WHOLESALE_VOLUME = 4.0
WHOLESALE_SHARE = 0.35

SCHEMA = """
CREATE TABLE sales (
    sale_id      INTEGER PRIMARY KEY,
    sale_date    TEXT NOT NULL,
    vendor       TEXT NOT NULL,
    fish_type    TEXT NOT NULL,
    kg_sold      REAL NOT NULL CHECK (kg_sold > 0),
    price_per_kg INTEGER NOT NULL CHECK (price_per_kg > 0),
    buyer_type   TEXT NOT NULL CHECK (buyer_type IN ('retail', 'wholesale'))
)
"""


def trading_days(start, end):
    """Every Monday to Saturday between start and end; the market rests on Sunday."""
    day = start
    while day <= end:
        if day.weekday() < 6:
            yield day
        day += timedelta(days=1)


def build_rows(rng):
    days = list(trading_days(START, END))
    names = list(VENDORS)
    weights = np.array(list(VENDORS.values()))
    weights = weights / weights.sum()
    fish_names = list(FISH)

    rows = []
    for i, day in enumerate(days):
        progress = i / (len(days) - 1)
        # More vendors log their sales as the quarter goes on: about 2 a day in
        # early August, closer to 3 by late October.
        sales_today = rng.poisson(2.0 + 1.2 * progress)
        for _ in range(sales_today):
            vendor = rng.choice(names, p=weights)
            fish = rng.choice(fish_names, p=[0.4, 0.25, 0.25, 0.1])
            base_price, base_kg = FISH[fish]
            wholesale = rng.random() < WHOLESALE_SHARE

            price = base_price * rng.normal(1.0, 0.06)
            kg = base_kg * rng.lognormal(0, 0.35) * (1 + 0.25 * progress)
            if wholesale:
                price *= WHOLESALE_DISCOUNT
                kg *= WHOLESALE_VOLUME

            rows.append((
                day.isoformat(),
                str(vendor),
                str(fish),
                round(float(kg), 1),
                int(round(price / 5) * 5),  # stalls quote in multiples of KES 5
                "wholesale" if wholesale else "retail",
            ))
    return rows


def main():
    rng = np.random.default_rng(SEED)
    rows = build_rows(rng)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(SCHEMA)
        conn.executemany(
            "INSERT INTO sales (sale_date, vendor, fish_type, kg_sold, "
            "price_per_kg, buyer_type) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        # The trend question groups by date, so the date gets the index.
        conn.execute("CREATE INDEX idx_sales_date ON sales(sale_date)")
        conn.commit()

        count, first, last, kg, revenue = conn.execute(
            "SELECT COUNT(*), MIN(sale_date), MAX(sale_date), SUM(kg_sold), "
            "SUM(kg_sold * price_per_kg) FROM sales"
        ).fetchone()
        mix = conn.execute(
            "SELECT buyer_type, COUNT(*) FROM sales GROUP BY buyer_type"
        ).fetchall()

    print(f"Wrote {count} sales to {DB_PATH}")
    print(f"Period: {first} to {last}")
    print("Buyer mix: " + ", ".join(f"{n} {t}" for t, n in mix))
    print(f"Fish sold: {kg:,.1f} kg for KES {revenue:,.0f}")


if __name__ == "__main__":
    main()
