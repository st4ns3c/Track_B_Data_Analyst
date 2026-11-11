"""
Nairobi Produce Market: sample daily prices
-------------------------------------------
Build plan
  Problem : a market analyst wants to know which of five vegetables has the
            most volatile price, and when that price peaks.
  Input   : none. This script makes the data.
  Output  : data/vegetable_prices.csv, one row per vegetable per day for six
            months (date, vegetable, price_kes_per_kg).

Usage:
    python generate_sample_data.py

Requirements:
    pip install pandas numpy
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "data" / "vegetable_prices.csv"

SEED = 15
START = "2026-05-01"
END = "2026-10-31"

# Base price, seasonal bump size, bump centre (days from 1 May), bump width,
# and day-to-day noise. Tomatoes get the biggest seasonal swing; onions the
# smallest. These are the patterns a market analyst would actually see.
VEGETABLES = {
    "Tomatoes": dict(base=85, amplitude=0.65, centre=130, width=25, noise=0.07),
    "Kale":     dict(base=35, amplitude=0.18, centre=160, width=35, noise=0.06),
    "Onions":   dict(base=110, amplitude=0.08, centre=100, width=40, noise=0.04),
    "Cabbage":  dict(base=45, amplitude=0.22, centre=140, width=30, noise=0.06),
    "Potatoes": dict(base=70, amplitude=0.15, centre=150, width=35, noise=0.05),
}


def build_prices():
    rng = np.random.default_rng(SEED)
    dates = pd.date_range(START, END, freq="D")
    day_number = np.arange(len(dates))

    # Weekend market prices run a little higher.
    weekend = np.where(dates.dayofweek >= 5, 1.03, 1.0)

    rows = []
    for vegetable, config in VEGETABLES.items():
        seasonal = config["amplitude"] * np.exp(
            -((day_number - config["centre"]) / config["width"]) ** 2
        )
        noise = rng.normal(0, config["noise"], len(dates))
        price = config["base"] * (1 + seasonal + noise) * weekend

        # Tomatoes also get a smaller June bump, which makes their year look
        # like a real tomato year rather than one smooth curve.
        if vegetable == "Tomatoes":
            price *= 1 + 0.15 * np.exp(-((day_number - 60) / 18) ** 2)

        price = np.clip(np.round(price), 10, None).astype(int)

        for date, value in zip(dates, price):
            rows.append({"date": date, "vegetable": vegetable, "price_kes_per_kg": value})

    return pd.DataFrame(rows)


def main():
    df = build_prices()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, date_format="%Y-%m-%d")

    print(f"Wrote {len(df):,} rows to {OUT_PATH}")
    print(f"Period: {df['date'].min():%d %b %Y} to {df['date'].max():%d %b %Y}")
    for vegetable, group in df.groupby("vegetable"):
        print(f"  {vegetable:<9} KES {group['price_kes_per_kg'].min():>3} to "
              f"{group['price_kes_per_kg'].max():>3} per kg")


if __name__ == "__main__":
    main()
