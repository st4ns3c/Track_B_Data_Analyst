"""
Kisumu Schools: sample attendance and infrastructure data
---------------------------------------------------------
Build plan
  Problem : a Kisumu County education officer has attendance records in one
            file and school infrastructure in another, and wants to know
            whether schools with more classrooms have better attendance.
  Input   : none. This script makes the two files.
  Output  : data/attendance.csv      (school, average_attendance_pct, county)
            data/infrastructure.csv  (school_name, num_classrooms, water_access)

Both files are deliberately messy: different column names, different school
name formats, missing values and a duplicate row. Cleaning them is the
exercise.

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

SEED = 14

# Twenty schools in Kisumu County. The count is small because this is a
# sample, not a census.
SCHOOLS = [
    "Kisumu Boys High School",
    "Kisumu Girls High School",
    "Maseno School",
    "St. Mary's School",
    "Manyatta Primary School",
    "Obunga Primary School",
    "Nyalenda Primary School",
    "Kondele Primary School",
    "Nyamasaria Primary School",
    "Ahero Primary School",
    "Muhoroni Primary School",
    "Katito Primary School",
    "Sondu Primary School",
    "Awasi Primary School",
    "Chemelil Primary School",
    "Miwani Primary School",
    "Riat Hills Primary School",
    "Dunga Primary School",
    "Migosi Primary School",
    "Nyahera Primary School",
]

# Classrooms per school. Secondary schools have more; small primaries fewer.
CLASSROOMS = [24, 22, 28, 18, 12, 9, 10, 8, 11, 14, 13, 7, 15, 10, 16, 9, 12, 6, 13, 11]

# How the infrastructure file writes some of the names. Each of these is a
# naming inconsistency the clean-up has to handle.
MESSY_INFRA_NAMES = {
    0: "KISUMU BOYS HIGH SCHOOL",      # capitals
    2: "Maseno Sch",                   # abbreviation
    3: "St Marys School",              # punctuation dropped
    4: "Manyatta Pri Sch",             # abbreviations
    5: "Obunga Primary",               # "School" missing
    6: "  Nyalenda  Primary School ",  # extra spaces
    9: "Ahero Pry Sch",                # more abbreviations
}


def build_attendance(rng):
    """The attendance file, with a missing value and an untidy name."""
    water = rng.random(len(SCHOOLS)) < 0.6

    attendance = 64 + 1.15 * np.array(CLASSROOMS) + 3 * water + rng.normal(0, 5.5, len(SCHOOLS))
    attendance = np.clip(np.round(attendance, 1), 55, 99)

    df = pd.DataFrame({
        "school": SCHOOLS,
        "average_attendance_pct": attendance,
        "county": "Kisumu",
    })

    # Two schools did not report attendance this term.
    df.loc[7, "average_attendance_pct"] = np.nan   # Kondele
    df.loc[16, "average_attendance_pct"] = np.nan  # Riat Hills

    # One name arrived with a trailing space.
    df.loc[7, "school"] = df.loc[7, "school"] + " "

    return df


def build_infrastructure(rng):
    """The infrastructure file: messy names, missing values, a duplicate row."""
    df = pd.DataFrame({
        "school_name": SCHOOLS,
        "num_classrooms": CLASSROOMS,
        "water_access": np.where(rng.random(len(SCHOOLS)) < 0.6, "Yes", "No"),
    })

    # Apply the messy spelling variants.
    for index, messy_name in MESSY_INFRA_NAMES.items():
        df.loc[index, "school_name"] = messy_name

    # Missing values.
    df.loc[10, "num_classrooms"] = np.nan  # Muhoroni: not counted yet
    df.loc[4, "water_access"] = np.nan     # Manyatta: not recorded
    df.loc[12, "water_access"] = np.nan    # Sondu: not recorded

    # Dunga is not in this file at all; the office never received its form.
    df = df.drop(index=17)

    # A school that only appears in the infrastructure file.
    extra = pd.DataFrame([{
        "school_name": "Rusinga Primary School",
        "num_classrooms": 11,
        "water_access": "Yes",
    }])
    df = pd.concat([df, extra], ignore_index=True)

    # The same infrastructure row was entered twice.
    duplicate = df[df["school_name"] == "Kondele Primary School"]
    df = pd.concat([df, duplicate], ignore_index=True)

    return df


def main():
    rng = np.random.default_rng(SEED)
    attendance = build_attendance(rng)
    infrastructure = build_infrastructure(rng)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    attendance.to_csv(DATA_DIR / "attendance.csv", index=False)
    infrastructure.to_csv(DATA_DIR / "infrastructure.csv", index=False)

    print(f"attendance.csv     : {len(attendance)} rows, "
          f"{attendance['average_attendance_pct'].isna().sum()} missing attendance values")
    print(f"infrastructure.csv : {len(infrastructure)} rows, "
          f"{infrastructure['num_classrooms'].isna().sum()} missing classroom counts, "
          f"{infrastructure['water_access'].isna().sum()} missing water records, "
          f"1 duplicate row")


if __name__ == "__main__":
    main()
