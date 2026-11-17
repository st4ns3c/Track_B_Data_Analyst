"""
Child nutrition programme: six months of outcomes
-------------------------------------------------
Build plan
  Problem : a Nairobi NGO runs a child nutrition programme in three counties
            and has to show a donor what six months achieved.
  Input   : none. This script makes the data.
  Output  : data/nutrition_outcomes.csv, one row per child enrolled:
            participant_id, county, age_group, months_in_program,
            sessions_attended, weight_gain_kg.

The seed is fixed (23), so every run writes the same rows. Children joined
in waves between May and October 2026, so some have been in the programme
six months and some only one. Sessions run weekly: four a month.

The patterns the analysis should find:
  - Attendance drives weight gain. A child who comes to almost every
    session gains about twice as much a month as one who comes to fewer
    than half.
  - Kitui attends best and Turkana worst (families there travel furthest),
    so Kitui gains most. Within the same attendance level the counties are
    close, which means the county gap is mostly an attendance gap.
  - The youngest children (6 to 23 months) gain the most a month: catch-up
    growth is fastest at that age.

Usage:
    python generate_nutrition_data.py

Requirements:
    pip install numpy pandas
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "nutrition_outcomes.csv"

SEED = 23
SESSIONS_PER_MONTH = 4

# County: (children enrolled, typical share of sessions attended, small
# county effect on gain that attendance does not explain).
COUNTIES = {
    "Kitui": (130, 0.82, 1.03),
    "Marsabit": (115, 0.70, 1.00),
    "Turkana": (125, 0.56, 0.97),
}

# Age group: (share of enrolment, monthly gain in kg at full attendance).
AGE_GROUPS = {
    "6-23 months": (0.40, 0.42),
    "2-5 years": (0.40, 0.30),
    "6-10 years": (0.20, 0.24),
}


def build_rows(rng):
    age_names = list(AGE_GROUPS)
    age_shares = [AGE_GROUPS[a][0] for a in age_names]
    rows = []
    for county, (n, usual_attendance, county_effect) in COUNTIES.items():
        for _ in range(n):
            age = str(rng.choice(age_names, p=age_shares))
            months = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.08, 0.10, 0.14, 0.18, 0.22, 0.28]))
            offered = months * SESSIONS_PER_MONTH

            # Each family's attendance varies around the county's usual level.
            share = float(np.clip(rng.beta(8 * usual_attendance, 8 * (1 - usual_attendance)), 0.1, 1.0))
            attended = int(rng.binomial(offered, share))
            actual_share = attended / offered

            # A child gains something from the food basket alone; the rest
            # comes with each session (feeding, check-ups, follow-up).
            monthly = AGE_GROUPS[age][1] * (0.30 + 0.70 * actual_share) * county_effect
            gain = months * monthly + rng.normal(0, 0.12 * np.sqrt(months))
            rows.append((county, age, months, attended, round(float(gain), 2)))

    df = pd.DataFrame(rows, columns=["county", "age_group", "months_in_program",
                                     "sessions_attended", "weight_gain_kg"])
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    df.insert(0, "participant_id", [f"NP-{i:04d}" for i in range(1, len(df) + 1)])
    return df


def main():
    rng = np.random.default_rng(SEED)
    df = build_rows(rng)

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)

    print(f"Wrote {len(df)} children to {CSV_PATH}")
    print("By county: " + ", ".join(f"{c} {n}" for c, n in df["county"].value_counts().sort_index().items()))
    print("By age group: " + ", ".join(f"{a} {n}" for a, n in df["age_group"].value_counts().items()))
    print(f"Average time in programme: {df['months_in_program'].mean():.1f} months")


if __name__ == "__main__":
    main()
