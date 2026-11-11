"""
Distributor Performance: sample order data
------------------------------------------
Build plan
  Problem : a distributor sells fast-moving goods in Nairobi and Mombasa. The
            manager wants to know how the two months compare, which region
            carries the business, and which customers matter.
  Input   : none. This script makes the two monthly files.
  Output  : data/sales_august.csv     (client_name, county, qty, unit_price)
            data/sales_september.csv  (customer_name, region, quantity, price)

The two files use different column names and a few different customer-name
spellings, the same way two monthly exports usually do. Cleaning them is part
of the project.

Usage:
    python generate_sample_data.py

Requirements:
    pip install pandas numpy
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

SEED = 15

# Customer, August revenue target, September revenue target (KES).
# The three big Nairobi accounts grow; the smaller accounts shrink; six
# Mombasa accounts stop ordering altogether.
CUSTOMERS = {
    "Nairobi": [
        ("Kamau Stores", 200000, 270000),
        ("Otieno Wholesale", 160000, 216000),
        ("Hassan Traders", 120000, 162000),
        ("Nairobi Fresh Ltd", 60000, 40000),
        ("Eastleigh Distributors", 50000, 34000),
        ("Kenyatta Market Traders", 40000, 27000),
        ("Ngara Supplies", 30000, 20000),
        ("Industrial Area Depot", 25000, 16000),
        ("City Market Traders", 20000, 12000),
        ("Westlands Grocers", 15000, 9000),
    ],
    "Mombasa": [
        ("Mombasa Retail Hub", 55000, 32000),
        ("Likoni Traders", 45000, 25000),
        ("Nyali Mini Mart", 38000, 21000),
        ("Changamwe Stores", 32000, 18000),
        ("Bombolulu Shop", 28000, 15000),
        ("Diani Supplies", 24000, 12000),
        ("Kilifi Corner", 20000, 10000),
        ("Malindi Wholesale", 18000, 9000),
        ("Tudor Traders", 22000, 0),
        ("Mtwapa Mart", 18000, 0),
        ("Shanzu Shop", 15000, 0),
        ("Kongowea Traders", 12000, 0),
        ("Voi Road Supplies", 10000, 0),
        ("Ukunda Mart", 8000, 0),
    ],
}

PRODUCTS = [
    ("Unga 2kg", 180),
    ("Rice 5kg", 650),
    ("Cooking Oil 1L", 320),
    ("Sugar 1kg", 160),
    ("Soap 800g", 220),
]

# Nairobi orders are larger and less frequent; Mombasa orders are smaller and
# more frequent. That is what makes the order share differ from the revenue
# share later.
AVERAGE_LINE_SIZE = {"Nairobi": 18000, "Mombasa": 5000}

# A little mess in the customer names, of the kind monthly exports produce.
AUGUST_NAMES = {"Kamau Stores": "Kamau Stores ", "Otieno Wholesale": "Otieno  Wholesale"}
SEPTEMBER_NAMES = {"Kamau Stores": "kamau stores", "Likoni Traders": "LIKONI TRADERS"}


def clean_for_export(name, month):
    """Apply the month-specific name variant, or return the name unchanged."""
    if month == "August":
        return AUGUST_NAMES.get(name, name)
    return SEPTEMBER_NAMES.get(name, name)


def build_month(month, start, days, rng):
    """Create the order lines for one month."""
    rows = []
    for region, customers in CUSTOMERS.items():
        for customer, august_target, september_target in customers:
            target = august_target if month == "August" else september_target
            if target <= 0:
                continue  # this customer did not order in this month

            line_size = AVERAGE_LINE_SIZE[region]
            n_lines = max(2, int(round(target / line_size + rng.normal(0, 1.2))))
            line_revenue = rng.dirichlet(np.ones(n_lines)) * target

            for revenue in line_revenue:
                product, base_price = PRODUCTS[int(rng.integers(len(PRODUCTS)))]
                price = int(round(base_price * rng.uniform(0.97, 1.03) / 5) * 5)
                quantity = max(1, int(round(revenue / price)))
                date = start + pd.Timedelta(days=int(rng.integers(0, days)))

                rows.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "customer": clean_for_export(customer, month),
                    "region": region,
                    "product": product,
                    "quantity": quantity,
                    "price": price,
                })

    df = pd.DataFrame(rows).sort_values(["date", "customer"]).reset_index(drop=True)
    return df


def main():
    rng = np.random.default_rng(SEED)

    august = build_month("August", pd.Timestamp("2026-08-01"), 31, rng)
    september = build_month("September", pd.Timestamp("2026-09-01"), 30, rng)

    # The two exports name the same fields differently.
    august = august.rename(columns={
        "customer": "client_name", "region": "county",
        "quantity": "qty", "price": "unit_price",
    })
    september = september.rename(columns={
        "customer": "customer_name", "region": "region",
        "quantity": "quantity", "price": "price",
    })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    august.to_csv(DATA_DIR / "sales_august.csv", index=False)
    september.to_csv(DATA_DIR / "sales_september.csv", index=False)

    august_revenue = (august["qty"] * august["unit_price"]).sum()
    september_revenue = (september["quantity"] * september["price"]).sum()

    print(f"sales_august.csv    : {len(august)} order lines, KES {august_revenue:,.0f}")
    print(f"sales_september.csv : {len(september)} order lines, KES {september_revenue:,.0f}")


if __name__ == "__main__":
    main()
