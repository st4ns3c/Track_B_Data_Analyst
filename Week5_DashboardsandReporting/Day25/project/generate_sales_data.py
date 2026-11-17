"""
Otieno Wholesale Supplies: sample distributor sales
---------------------------------------------------
Build plan
  Problem : a Nairobi wholesaler wants a dashboard of its sales by county
            and month, with its top accounts and the shops that have
            stopped ordering.
  Input   : none. This script makes the data.
  Output  : data/sales_data.csv, one row per order line:
            order_id, date, customer, county, product, quantity, price.
            Revenue is quantity x price, as in the lesson.

The seed is fixed (25), so every run writes the same rows. The data runs
from Monday 1 June to Saturday 14 November 2026, Monday to Saturday.

Patterns for the dashboard to find:
  - Sales grow gently through the period, with a back-to-school dip in
    early September when shops' cash is tight.
  - A handful of large shops carry a big share of revenue.
  - Ten shops stop ordering at different points from August to October.
    Some were big accounts: this is the dormant-customer story.
  - Four shops join part-way through, so "new this month" is real.

Usage:
    python generate_sales_data.py

Requirements:
    pip install numpy pandas
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "sales_data.csv"

SEED = 25
START = date(2026, 6, 1)
END = date(2026, 11, 14)

# Product: (unit sold, typical price in KES per unit, typical units per line).
PRODUCTS = {
    "Maize flour 2kg (bale of 12)": (1850, 8),
    "Rice 25kg bag": (4200, 3),
    "Sugar 50kg bag": (7600, 2),
    "Cooking oil 20L jerrycan": (5400, 2),
    "Wheat flour 2kg (bale of 12)": (2100, 5),
    "Bar soap (carton)": (1650, 4),
    "Tea leaves 500g (carton of 20)": (3900, 2),
    "Salt 1kg (bale of 20)": (650, 6),
}
PRODUCT_WEIGHTS = [0.24, 0.14, 0.12, 0.12, 0.12, 0.10, 0.08, 0.08]

COUNTIES = {"Nairobi": 0.38, "Kiambu": 0.22, "Machakos": 0.15, "Kajiado": 0.13, "Nakuru": 0.12}

SHOP_NAMES = [
    "Mama Njeri Shop", "Kamau General Store", "Wanjiku Mini Mart", "Baraka Retailers",
    "Achieng Provision Store", "Mutua Wholesalers", "Kipchoge Duka", "Faith Supermarket",
    "Neema Shop", "Jamii Stores", "Upendo Mini Market", "Kilimani Grocers",
    "Riziki Traders", "Imani General Shop", "Tumaini Stores", "Mwangi & Sons",
    "Ochieng Corner Shop", "Wambui Retail", "Karibu Mini Mart", "Mlimani Stores",
    "Amani Duka", "Juja Road Traders", "Gikomba Provisions", "Ruiru Fresh Mart",
    "Thika Town Stores", "Githurai Mini Mart", "Kitengela Supplies", "Ongata Shop",
    "Rongai Retailers", "Syokimau Stores", "Athi River Traders", "Mlolongo Mart",
    "Machakos Town Duka", "Kangundo Stores", "Nakuru Central Shop", "Naivasha Traders",
    "Gilgil General Store", "Molo Provisions", "Kikuyu Town Mart", "Limuru Stores",
    "Kiserian Shop", "Ngong Road Grocers", "Kasarani Supplies", "Embakasi Stores",
    "Pipeline Mini Mart", "Kayole Traders", "Utawala Shop", "Kahawa West Stores",
]
NEW_SHOPS = {"Ruai Fresh Stores": date(2026, 8, 17), "Tatu City Mart": date(2026, 9, 7),
             "Juja Farm Duka": date(2026, 10, 5), "Kamulu Traders": date(2026, 10, 19)}


def trading_days(start, end):
    day = start
    while day <= end:
        if day.weekday() < 6:
            yield day
        day += timedelta(days=1)


def make_customers(rng):
    customers = []
    names = SHOP_NAMES + list(NEW_SHOPS)
    county_names, county_p = list(COUNTIES), list(COUNTIES.values())
    # A few big accounts and many small ones: order size and frequency both
    # follow a skewed spread, which is how wholesale books usually look.
    sizes = rng.lognormal(0, 0.55, len(names))
    sizes[:5] *= 2.2
    dormant = rng.choice(np.arange(3, len(SHOP_NAMES)), size=10, replace=False)
    dormant[:3] = [0, 2, 6]  # three of the big accounts are among those going quiet
    for i, name in enumerate(names):
        stop = None
        if i in dormant:
            stop = START + timedelta(days=int(rng.integers(62, 135)))
        customers.append({
            "customer": name,
            "county": str(rng.choice(county_names, p=county_p)),
            "orders_per_week": float(np.clip(rng.gamma(2.5, 0.45), 0.25, 3.0)),
            "size": float(sizes[i]),
            "start": NEW_SHOPS.get(name, START),
            "stop": stop,
        })
    return customers


def season(day, progress):
    growth = 1 + 0.18 * progress
    # Back-to-school: shops spend on fees, not stock, for about two weeks.
    if date(2026, 8, 31) <= day <= date(2026, 9, 12):
        growth *= 0.72
    return growth


def build_rows(rng):
    customers = make_customers(rng)
    days = list(trading_days(START, END))
    product_names = list(PRODUCTS)
    rows = []
    order_id = 100000
    for i, day in enumerate(days):
        progress = i / (len(days) - 1)
        for c in customers:
            if day < c["start"] or (c["stop"] and day > c["stop"]):
                continue
            # Orders per trading day, from the shop's weekly habit.
            if rng.random() >= c["orders_per_week"] / 6 * season(day, progress):
                continue
            order_id += 1
            n_lines = int(rng.integers(1, 4))
            for product in rng.choice(product_names, size=n_lines, replace=False, p=PRODUCT_WEIGHTS):
                price, typical_qty = PRODUCTS[str(product)]
                qty = max(1, int(round(rng.lognormal(np.log(typical_qty * c["size"]), 0.35))))
                unit_price = int(round(price * rng.normal(1 + 0.04 * progress, 0.015) / 10) * 10)
                rows.append((f"ORD-{order_id}", day.isoformat(), c["customer"], c["county"],
                             str(product), qty, unit_price))
    return pd.DataFrame(rows, columns=["order_id", "date", "customer", "county",
                                       "product", "quantity", "price"])


def main():
    rng = np.random.default_rng(SEED)
    df = build_rows(rng)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)

    revenue = (df["quantity"] * df["price"]).sum()
    print(f"Wrote {len(df):,} order lines ({df['order_id'].nunique():,} orders) to {CSV_PATH}")
    print(f"Period: {df['date'].min()} to {df['date'].max()}")
    print(f"Customers: {df['customer'].nunique()}, revenue KES {revenue:,.0f}")


if __name__ == "__main__":
    main()
