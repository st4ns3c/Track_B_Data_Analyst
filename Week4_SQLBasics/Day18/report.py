"""
Nairobi wholesale distributor: Monday county report
---------------------------------------------------
Build plan
  Problem : the operations team runs the same county report by hand in a
            database tool every week. They want one Python function they can
            run on any machine.
  Input   : data/sales.db, built by generate_sales_data.py.
  Output  : a pandas DataFrame with product, total_orders, total_quantity and
            total_revenue_kes for one county and date range. The demo at the
            bottom runs three county/date combinations plus an empty result.

Usage:
    python generate_sales_data.py
    python report.py

Requirements:
    pip install pandas
"""

import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "sales.db"

REPORT_COLUMNS = [
    "product",
    "total_orders",
    "total_quantity",
    "total_revenue_kes",
]

# The ? placeholders are filled by pandas, never by string formatting. That
# keeps a county name with an apostrophe or a quote harmless.
REPORT_QUERY = """
    SELECT product,
           COUNT(*) AS total_orders,
           SUM(quantity) AS total_quantity,
           SUM(quantity * unit_price) AS total_revenue_kes
    FROM orders
    WHERE LOWER(county) = LOWER(?)
      AND order_date BETWEEN ? AND ?
    GROUP BY product
    ORDER BY total_revenue_kes DESC, product
"""

DISPLAY_COLUMNS = {
    "product": "Product",
    "total_orders": "Orders",
    "total_quantity": "Units",
    "total_revenue_kes": "Revenue (KES)",
}


class ReportError(Exception):
    """Raised when the report can't be built, with a message an operator understands."""


def parse_date(value, label):
    """Return an ISO date string, or explain which argument is wrong."""
    if isinstance(value, datetime):
        text = value.date().isoformat()
    elif isinstance(value, date):
        text = value.isoformat()
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ReportError(f"{label} must be a date like 2026-08-01.")

    if not text:
        raise ReportError(f"{label} cannot be empty.")

    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ReportError(f"{label} must be a real date in YYYY-MM-DD format, "
                          f"like 2026-08-01.")

    return parsed.isoformat()


def connect():
    """Open the sales database read-only, so the report can't change the source."""
    if not DB_PATH.exists():
        raise ReportError(f"Can't find {DB_PATH}. Run generate_sales_data.py first.")

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM orders LIMIT 1").fetchone()
    except sqlite3.Error as error:
        if "conn" in locals():
            conn.close()
        raise ReportError(f"{DB_PATH.name} is not a usable sales database "
                          f"({error}). Run generate_sales_data.py again.")

    return conn


def get_county_report(county, start_date, end_date):
    """Product summary for one county between two dates, inclusive.

    Returns a DataFrame with the columns:
        product, total_orders, total_quantity, total_revenue_kes
    An unknown county or an empty date range returns an empty DataFrame with
    the same columns, not an error.
    """
    county = "" if county is None else str(county).strip()
    if not county:
        raise ReportError("County cannot be empty. Try 'Mombasa'.")

    start = parse_date(start_date, "Start date")
    end = parse_date(end_date, "End date")
    if start > end:
        raise ReportError("Start date must be on or before the end date.")

    conn = connect()
    try:
        report = pd.read_sql_query(
            REPORT_QUERY,
            conn,
            params=(county, start, end),
        )
    except sqlite3.Error as error:
        raise ReportError(f"The report query failed: {error}")
    finally:
        conn.close()

    if report.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    report["total_orders"] = report["total_orders"].astype(int)
    report["total_quantity"] = report["total_quantity"].astype(int)
    report["total_revenue_kes"] = report["total_revenue_kes"].astype(float)
    return report[REPORT_COLUMNS]


def format_report(report):
    """Friendly column names and thousands separators for the screen."""
    table = report.rename(columns=DISPLAY_COLUMNS)
    table["Orders"] = table["Orders"].map(lambda value: f"{value:,}")
    table["Units"] = table["Units"].map(lambda value: f"{value:,}")
    table["Revenue (KES)"] = table["Revenue (KES)"].map(lambda value: f"{value:,.0f}")
    return table.to_string(index=False)


def main():
    examples = [
        ("Mombasa", "2026-08-01", "2026-09-30"),
        ("Kisumu", "2026-09-01", "2026-10-31"),
        ("Nairobi", "2026-08-01", "2026-10-31"),
        ("Garissa", "2026-08-01", "2026-10-31"),
    ]

    print("Nairobi Wholesale Distributor: county report examples")
    print(f"Database: {DB_PATH}\n")

    try:
        for county, start, end in examples:
            report = get_county_report(county, start, end)
            print(f"{county}: {start} to {end}")
            if report.empty:
                print("  No orders found for that county and period.\n")
            else:
                print(format_report(report))
                print()
    except ReportError as error:
        sys.exit(f"Can't build the report. {error}")


if __name__ == "__main__":
    main()
