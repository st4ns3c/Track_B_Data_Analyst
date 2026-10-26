"""
Dairy Co-op Zone Summary
------------------------
Build plan
  Problem    : a Nakuru dairy co-op manager keeps milk collection and farmer
               details in two separate spreadsheets, and wants one table per
               zone for the month.
  Input      : milk_collection.csv  (farmer_name, date, litres)
               farmer_details.csv   (farmer_name, zone, rate_kes_per_litre)
  Processing : clean the names, merge the two on farmer_name, work out each
               delivery's payout, pivot by zone, find the top farmer per zone.
  Output     : a summary table (total litres, total payout, top farmer per
               zone) printed for a screenshot, and saved as a CSV for Excel.

Usage:
    python zone_summary.py
    python zone_summary.py path/to/milk_collection.csv path/to/farmer_details.csv

Requirements:
    pip install pandas
"""

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DEFAULT_COLLECTION = BASE_DIR / "data" / "milk_collection.csv"
DEFAULT_DETAILS = BASE_DIR / "data" / "farmer_details.csv"
OUTPUT_DIR = BASE_DIR / "output"

COOP_NAME = "Nakuru Dairy Co-op"


class DataError(Exception):
    """Raised when an input file can't be used, with a message for the manager."""


def load_csv(path, columns):
    """Read a CSV and check it has the columns we need."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}.")
    missing = set(columns) - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): {', '.join(sorted(missing))}. "
                        f"Expected: {', '.join(columns)}.")
    return df[columns]


def clean_name(name):
    """'jane wanjiku ' and 'Jane  Wanjiku' are the same farmer -> 'Jane Wanjiku'."""
    return " ".join(str(name).split()).title()


def load_data(collection_path, details_path):
    collection = load_csv(collection_path, ["farmer_name", "date", "litres"])
    details = load_csv(details_path, ["farmer_name", "zone", "rate_kes_per_litre"])

    # The merge is on the name, so the names have to match exactly in both files.
    collection["farmer_name"] = collection["farmer_name"].apply(clean_name)
    details["farmer_name"] = details["farmer_name"].apply(clean_name)

    collection["date"] = pd.to_datetime(collection["date"], errors="coerce")
    bad_dates = collection["date"].isna().sum()
    if bad_dates:
        raise DataError(f"{bad_dates} row(s) in {Path(collection_path).name} have a date that "
                        "isn't a real date. Use the format 2026-10-25.")

    # A farmer listed twice in the details sheet would have every delivery
    # counted twice after the merge, so stop before that happens.
    repeated = details.loc[details["farmer_name"].duplicated(), "farmer_name"]
    if not repeated.empty:
        raise DataError(f"These farmers appear more than once in {Path(details_path).name}: "
                        f"{', '.join(repeated.unique())}. Each farmer should have one row.")
    return collection, details


def this_month(collection):
    """Keep only the latest month in the collection sheet: 'this month'."""
    month = collection["date"].dt.to_period("M").max()
    return collection[collection["date"].dt.to_period("M") == month], month


def merge_farmers(collection, details):
    """Join each delivery to its farmer's zone and rate.

    A left join keeps every delivery, even from a farmer missing in the
    details sheet. Those can't be paid (no rate), so they're split out and
    reported instead of silently disappearing like they would in an inner join.
    """
    merged = pd.merge(collection, details, on="farmer_name", how="left",
                      validate="many_to_one", indicator=True)

    unmatched = merged[merged["_merge"] == "left_only"]
    matched = merged[merged["_merge"] == "both"].drop(columns="_merge")

    matched = matched.assign(payout_kes=matched["litres"] * matched["rate_kes_per_litre"])
    missing = unmatched.groupby("farmer_name")["litres"].sum()
    return matched, missing


def zone_summary(merged):
    """One row per zone: total litres, total payout and the top farmer."""
    totals = pd.pivot_table(merged, index="zone", values=["litres", "payout_kes"], aggfunc="sum")

    per_farmer = merged.groupby(["zone", "farmer_name"], as_index=False)["litres"].sum()
    # For each zone, the row of the farmer with the most litres.
    top = per_farmer.loc[per_farmer.groupby("zone")["litres"].idxmax()].set_index("zone")

    summary = pd.DataFrame({
        "total_litres": totals["litres"],
        "total_payout_kes": totals["payout_kes"].round(2),
        "top_farmer": top["farmer_name"],
        "top_farmer_litres": top["litres"],
    })
    return summary.sort_values("total_payout_kes", ascending=False)


def print_report(summary, month, merged, missing):
    first, last = merged["date"].min(), merged["date"].max()
    farmers = merged["farmer_name"].nunique()

    # Labels for the "Top farmer" column, built row by row with apply().
    top_label = summary.apply(lambda row: f"{row['top_farmer']} ({row['top_farmer_litres']:,.1f} L)", axis=1)

    line = "-" * 79
    print()
    print(f"  {COOP_NAME}: Zone Summary, {month.strftime('%B %Y')}")
    print(f"  Deliveries {first:%d %b} to {last:%d %b %Y} · {farmers} farmers · {len(merged)} deliveries")
    print("  " + line)
    print(f"  {'Zone':<10}{'Total litres':>14}{'Total payout (KES)':>21}   {'Top farmer'}")
    print("  " + line)
    for zone, row in summary.iterrows():
        print(f"  {zone:<10}{row['total_litres']:>14,.1f}{row['total_payout_kes']:>21,.2f}   {top_label[zone]}")
    print("  " + line)
    print(f"  {'ALL ZONES':<10}{summary['total_litres'].sum():>14,.1f}{summary['total_payout_kes'].sum():>21,.2f}")
    print("  " + line)

    if not missing.empty:
        print()
        print("  Not included (no zone or rate in the farmer details sheet):")
        for name, litres in missing.items():
            print(f"    - {name}: {litres:,.1f} L delivered. Add them to farmer_details.csv and run again.")
    print()


def main():
    if len(sys.argv) == 3:
        collection_path, details_path = Path(sys.argv[1]), Path(sys.argv[2])
    elif len(sys.argv) == 1:
        collection_path, details_path = DEFAULT_COLLECTION, DEFAULT_DETAILS
    else:
        print("Usage: python zone_summary.py [milk_collection.csv farmer_details.csv]")
        raise SystemExit(1)

    try:
        collection, details = load_data(collection_path, details_path)
    except DataError as error:
        print(f"Can't build the summary. {error}")
        raise SystemExit(1)

    collection, month = this_month(collection)
    merged, missing = merge_farmers(collection, details)
    summary = zone_summary(merged)

    print_report(summary, month, merged, missing)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_file = OUTPUT_DIR / f"zone_summary_{month}.csv"
    summary.to_csv(out_file, index_label="zone")
    print(f"  Saved for Excel: {out_file.relative_to(BASE_DIR)}")
    print()


if __name__ == "__main__":
    main()
