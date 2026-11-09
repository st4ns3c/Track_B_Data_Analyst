"""
Mombasa Microfinance: sample loan data
--------------------------------------
Build plan
  Problem : a Mombasa microfinance institution wants to describe its loan book
            to the board: typical loan size, unusual loans, and whether loan
            size relates to how quickly the first repayment arrives.
  Input   : none. This script makes the data.
  Output  : data/loans.csv, 150 fictional loan records.

Usage:
    python generate_sample_data.py

Requirements:
    pip install pandas numpy
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "data" / "loans.csv"

N_LOANS = 150
SEED = 13

COUNTIES = ["Mombasa", "Kilifi", "Kwale", "Taita Taveta", "Lamu"]
COUNTY_WEIGHTS = [0.45, 0.20, 0.15, 0.10, 0.10]

# First repayment is a little later outside Mombasa, where branches are
# further from the borrower.
COUNTY_DAYS = {"Mombasa": 0, "Kilifi": 3, "Kwale": 4, "Taita Taveta": 6, "Lamu": 5}


def build_loans():
    rng = np.random.default_rng(SEED)

    # Most microfinance loans are small. A log-normal shape gives a long right
    # tail, which is what real loan books look like: many modest loans and a
    # few large ones. Rounded to the nearest KES 500.
    amounts = np.round(np.exp(rng.normal(10.35, 0.50, N_LOANS)) / 500) * 500
    amounts = np.clip(amounts, 3000, 160000)

    # A handful of genuinely large loans. The board will ask about these, so
    # they belong in the data rather than being quietly removed.
    large = rng.choice(N_LOANS, size=4, replace=False)
    amounts[large] = [480000, 650000, 820000, 950000]

    # And a few very small ones, of the kind a first-time borrower takes.
    small = rng.choice([i for i in range(N_LOANS) if i not in large], size=3, replace=False)
    amounts[small] = [2500, 3000, 4000]

    counties = rng.choice(COUNTIES, size=N_LOANS, p=COUNTY_WEIGHTS)
    county_days = np.array([COUNTY_DAYS[c] for c in counties])

    # Larger loans tend to take slightly longer to reach a first repayment,
    # plus normal variation and the county effect. This is a tendency, not a
    # rule: many small loans are late and some large ones are early.
    days = 15 + 7 * np.log(amounts / 30000) + county_days + rng.normal(0, 5, N_LOANS)

    # A few slow first repayments, the sort of account a credit officer would
    # already be following up.
    late = rng.choice([i for i in range(N_LOANS) if i not in large], size=3, replace=False)
    days[late] = [62, 74, 88]

    days = np.clip(np.round(days), 3, None).astype(int)

    # Shuffle so the large loans are not sitting together at the end.
    order = rng.permutation(N_LOANS)
    amounts, days, counties = amounts[order], days[order], counties[order]
    loan_ids = [f"ML-2026-{i:03d}" for i in range(1, N_LOANS + 1)]

    return pd.DataFrame({
        "loan_id": loan_ids,
        "amount_kes": amounts.astype(int),
        "days_to_first_repayment": days,
        "county": counties,
    })


def main():
    df = build_loans()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(df)} loans to {OUT_PATH}")
    print(f"Amount range: KES {df['amount_kes'].min():,} to {df['amount_kes'].max():,} "
          f"(median KES {df['amount_kes'].median():,.0f})")
    print(f"Days to first repayment: {df['days_to_first_repayment'].min()} to "
          f"{df['days_to_first_repayment'].max()} (median "
          f"{df['days_to_first_repayment'].median():.0f})")
    print("Counties: " + ", ".join(f"{c} {n}" for c, n in df["county"].value_counts().items()))


if __name__ == "__main__":
    main()
