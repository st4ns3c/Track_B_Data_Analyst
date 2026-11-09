"""
Supermarket Foot Traffic: sample data
-------------------------------------
Build plan
  Problem : a Nairobi supermarket chain has 18 months of daily transaction
            counts and wants to know whether foot traffic is growing or just
            moving with the seasons.
  Input   : none. This script makes the data.
  Output  : data/daily_transactions.csv, one row per day.

Usage:
    python generate_sample_data.py

Requirements:
    pip install pandas numpy
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "data" / "daily_transactions.csv"

# 18 months, chosen so the data holds two festive seasons and two February
# dips. One December on its own can't show a pattern, only a spike.
START = "2024-12-01"
END = "2026-05-31"
SEED = 12

# How busy each month usually is, against an ordinary month. December is the
# Christmas rush; February is the quiet month after the school fees are paid.
MONTH_FACTOR = {
    1: 1.02, 2: 0.78, 3: 0.96, 4: 0.95, 5: 0.99, 6: 1.00,
    7: 0.97, 8: 1.01, 9: 1.00, 10: 1.04, 11: 1.18, 12: 1.38,
}

# Saturday is the big shopping day; Monday and Tuesday are the quietest.
WEEKDAY_FACTOR = {0: 0.92, 1: 0.90, 2: 0.94, 3: 1.00, 4: 1.16, 5: 1.31, 6: 1.15}


def build_daily_data():
    """Return dates and transaction counts for the whole period."""
    rng = np.random.default_rng(SEED)
    dates = pd.date_range(START, END, freq="D")
    n = len(dates)

    # Slow, steady growth: about 30% more customers a day by the end.
    trend = np.linspace(1.0, 1.30, n)

    month = np.array([MONTH_FACTOR[d.month] for d in dates])
    weekday = np.array([WEEKDAY_FACTOR[d.dayofweek] for d in dates])

    # Payday weeks at the start and end of the month are a little busier.
    day = dates.day.to_numpy()
    payday = np.where((day <= 5) | (day >= 27), 1.07, 1.0)

    # Some months are simply better than others, beyond the seasonal pattern.
    first = dates[0]
    month_offset = (dates.year - first.year) * 12 + dates.month - first.month
    month_noise = rng.normal(1.0, 0.04, size=18)[month_offset]

    daily_noise = rng.normal(1.0, 0.055, size=n)

    base = 900
    transactions = base * trend * month * weekday * payday * month_noise * daily_noise
    transactions = np.clip(np.round(transactions), 250, None).astype(int)

    # A handful of promotion days give the kind of obvious spikes a manager
    # would ask about.
    promo_days = rng.choice(n, size=7, replace=False)
    transactions[promo_days] = (transactions[promo_days] * 1.35).astype(int)

    return pd.DataFrame({"date": dates, "transactions": transactions})


def main():
    df = build_daily_data()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, date_format="%Y-%m-%d")

    print(f"Wrote {len(df)} days to {OUT_PATH}")
    print(f"Period: {df['date'].min():%d %b %Y} to {df['date'].max():%d %b %Y}")
    print(f"Daily transactions: {df['transactions'].min():,} to {df['transactions'].max():,} "
          f"(average {df['transactions'].mean():,.0f})")


if __name__ == "__main__":
    main()
