"""
Nakuru school attendance: sample data for the dashboard
-------------------------------------------------------
Build plan
  Problem : a school principal in Nakuru wants to check attendance on her
            phone every morning instead of opening Excel.
  Input   : none. This script makes the data.
  Output  : data/attendance.csv with one row per class per school day:
            date, class_name, students_present, students_total.

The seed is fixed (21), so every run writes the same rows. The data covers
ten weeks of Term 3 2026 (Monday 24 August to Friday 30 October) for five
classes. It has the patterns a real register has, so the dashboard has
something to find:
  - Mondays and Fridays run a little lower than midweek.
  - A wet week in late September pulls every class down.
  - No school on Mashujaa Day (Tuesday 20 October).
  - Form 3 slides steadily over the last four weeks. This is the decline the
    principal wants to be able to spot.

Usage:
    python generate_attendance_data.py

Requirements:
    pip install numpy pandas
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "attendance.csv"

SEED = 21
START = date(2026, 8, 24)
END = date(2026, 10, 30)
HOLIDAYS = {date(2026, 10, 20)}  # Mashujaa Day
WET_WEEK = (date(2026, 9, 21), date(2026, 9, 25))
DECLINE_FROM = date(2026, 10, 5)

# Class name: (students on the register, usual attendance rate).
CLASSES = {
    "Grade 7": (46, 0.95),
    "Grade 8": (44, 0.93),
    "Grade 9": (48, 0.92),
    "Form 3": (42, 0.91),
    "Form 4": (40, 0.94),
}

# Monday to Friday; weekends get no row.
WEEKDAY_EFFECT = {0: -0.02, 1: 0.0, 2: 0.01, 3: 0.0, 4: -0.025}


def school_days(start, end):
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in HOLIDAYS:
            yield day
        day += timedelta(days=1)


def build_rows(rng):
    rows = []
    for day in school_days(START, END):
        for name, (total, usual) in CLASSES.items():
            rate = usual + WEEKDAY_EFFECT[day.weekday()]
            if WET_WEEK[0] <= day <= WET_WEEK[1]:
                rate -= 0.05
            if name == "Form 3" and day >= DECLINE_FROM:
                # About 1.5 points lower each week, so the drop shows up as a
                # trend rather than a single bad day.
                weeks_in = (day - DECLINE_FROM).days / 7
                rate -= 0.015 * (weeks_in + 1)
            rate = float(np.clip(rate, 0.5, 1.0))
            present = int(rng.binomial(total, rate))
            rows.append((day.isoformat(), name, present, total))
    return pd.DataFrame(
        rows, columns=["date", "class_name", "students_present", "students_total"]
    )


def main():
    rng = np.random.default_rng(SEED)
    df = build_rows(rng)

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)

    days = df["date"].nunique()
    rate = df["students_present"].sum() / df["students_total"].sum()
    print(f"Wrote {len(df)} rows to {CSV_PATH}")
    print(f"Period: {df['date'].min()} to {df['date'].max()} ({days} school days)")
    print(f"Classes: {', '.join(CLASSES)}")
    print(f"Overall attendance: {rate:.1%}")


if __name__ == "__main__":
    main()
