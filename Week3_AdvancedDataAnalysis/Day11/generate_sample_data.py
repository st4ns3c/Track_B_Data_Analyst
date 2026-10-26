"""
Sample Data Generator
---------------------
Creates the two spreadsheets the co-op manager would send, as CSV files:

    data/farmer_details.csv   farmer_name, zone, rate_kes_per_litre
    data/milk_collection.csv  farmer_name, date, litres

14 farmers in 3 Nakuru zones, one row per farmer per delivery day for
1 to 25 October 2026. The random seed is fixed, so every run gives the
same files.

Real spreadsheets are never perfectly clean, so a few things are left in
on purpose, the way a clerk would type them:
  - some names have different capitals or extra spaces ("jane wanjiku ")
  - farmers sometimes miss a day (sick cow, rain, no transport)
  - one new farmer delivers milk but isn't in the details sheet yet

Usage:
    python generate_sample_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
SEED = 11

# name, zone, rate per litre (KES), usual litres per day
# Rates differ by zone (distance to the cooling plant) and by milk quality.
FARMERS = [
    ("Jane Wanjiku",    "Bahati",  52.0, 42),
    ("Peter Kamau",     "Bahati",  52.0, 18),
    ("Grace Njeri",     "Bahati",  53.5, 27),
    ("Joseph Mwangi",   "Bahati",  52.0, 9),
    ("Esther Wairimu",  "Bahati",  53.5, 33),
    ("Daniel Kiprotich", "Njoro",  50.0, 55),
    ("Mercy Chebet",    "Njoro",   50.0, 21),
    ("Samuel Langat",   "Njoro",   51.5, 30),
    ("Ann Jepkoech",    "Njoro",   50.0, 12),
    ("John Kariuki",    "Subukia", 54.0, 25),
    ("Lucy Wambui",     "Subukia", 54.0, 38),
    ("David Ndungu",    "Subukia", 55.0, 16),
    ("Mary Nyambura",   "Subukia", 54.0, 47),
    ("Francis Gitau",   "Subukia", 55.0, 11),
]

# Delivers milk but the manager hasn't added him to the details sheet yet.
NEW_FARMER = ("Kevin Rotich", 14)

# How the clerk sometimes types a name in the collection sheet.
TYPOS = {
    "Jane Wanjiku": "jane wanjiku ",
    "Daniel Kiprotich": "Daniel  Kiprotich",
    "Lucy Wambui": "LUCY WAMBUI",
}


def main():
    rng = np.random.default_rng(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    details = pd.DataFrame(
        [(name, zone, rate) for name, zone, rate, _ in FARMERS],
        columns=["farmer_name", "zone", "rate_kes_per_litre"],
    )
    details.to_csv(DATA_DIR / "farmer_details.csv", index=False)

    dates = pd.date_range("2026-10-01", "2026-10-25", freq="D")
    rows = []
    herds = [(name, usual) for name, _, _, usual in FARMERS] + [NEW_FARMER]
    for name, usual in herds:
        for date in dates:
            # About 1 day in 15 there's no delivery.
            if rng.random() < 0.07:
                continue
            # Daily yield moves around the farmer's usual amount, to the half litre.
            litres = max(1.0, round(rng.normal(usual, usual * 0.12) * 2) / 2)
            # Now and then the clerk types the name differently.
            typed_name = TYPOS[name] if name in TYPOS and rng.random() < 0.3 else name
            rows.append((typed_name, date.strftime("%Y-%m-%d"), litres))

    collection = pd.DataFrame(rows, columns=["farmer_name", "date", "litres"])
    # Sorted by date, the way a daily collection log is kept.
    collection = collection.sort_values(["date", "farmer_name"], kind="stable")
    collection.to_csv(DATA_DIR / "milk_collection.csv", index=False)

    print(f"Wrote {len(details)} farmers to {DATA_DIR / 'farmer_details.csv'}")
    print(f"Wrote {len(collection)} deliveries to {DATA_DIR / 'milk_collection.csv'}")


if __name__ == "__main__":
    main()
