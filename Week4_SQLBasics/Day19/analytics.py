"""
Nairobi wholesale distributor: analytical queries for the board
---------------------------------------------------------------
Build plan
  Problem : the CFO wants trend analysis, not another totals report. Three
            board questions came up that nobody could answer quickly: the
            status mix per county, which customers are growing month on
            month, and how revenue accumulates through the quarter.
  Input   : data/analytics.db, built by generate_analytical_data.py.
  Output  : the three queries printed as clean tables with pandas, plus an
            EXPLAIN QUERY PLAN check that shows the county index in use.

Usage:
    python generate_analytical_data.py
    python analytics.py

Requirements:
    pip install pandas
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "analytics.db"

# Q1: status mix per county.
# Interpretation: every county completes at least half of its orders, but
# Mombasa and Machakos cancel one order in four, double the network average,
# so the fulfilment problem is regional rather than company-wide.
Q1_STATUS_MIX = """
    SELECT c.county,
           COUNT(*) AS total_orders,
           SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) AS completed,
           SUM(CASE WHEN o.status = 'pending'   THEN 1 ELSE 0 END) AS pending,
           SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
           ROUND(100.0 * SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS completed_pct,
           ROUND(100.0 * SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS pending_pct,
           ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS cancelled_pct
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.county
    ORDER BY cancelled_pct DESC, c.county
"""

# Q2: customers whose monthly order value rose in two consecutive months.
# Interpretation: only Kamau Stores and Njeri Enterprises grew in both
# September and October, and both are modest accounts, so the growth story is
# coming from customers the board has not been watching.
Q2_MONTH_ON_MONTH = """
    WITH monthly AS (
        SELECT c.customer_id,
               c.customer_name,
               c.county,
               strftime('%Y-%m', o.order_date) AS month,
               CAST(strftime('%Y', o.order_date) AS INTEGER) * 12
                 + CAST(strftime('%m', o.order_date) AS INTEGER) AS month_no,
               SUM(o.quantity * o.unit_price) AS month_value
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.status <> 'cancelled'
        GROUP BY c.customer_id, c.customer_name, c.county, month, month_no
    ),
    compared AS (
        SELECT customer_id, customer_name, county, month, month_no, month_value,
               LAG(month_value) OVER w AS previous_value,
               LAG(month) OVER w AS previous_month,
               LAG(month_no) OVER w AS previous_month_no
        FROM monthly
        WINDOW w AS (PARTITION BY customer_id ORDER BY month_no)
    ),
    flagged AS (
        SELECT customer_id, customer_name, county, month, month_value,
               previous_value, previous_month,
               CASE WHEN previous_value IS NOT NULL
                         AND month_no - previous_month_no = 1
                         AND month_value > previous_value
                    THEN 1 ELSE 0 END AS increased
        FROM compared
    ),
    streaks AS (
        SELECT *,
               LAG(increased) OVER (
                   PARTITION BY customer_id ORDER BY month
               ) AS previous_increased
        FROM flagged
    ),
    qualifying AS (
        SELECT DISTINCT customer_id
        FROM streaks
        WHERE increased = 1 AND previous_increased = 1
    )
    SELECT customer_name,
           county,
           month,
           previous_month,
           previous_value,
           month_value,
           month_value - previous_value AS growth_value,
           ROUND(100.0 * (month_value - previous_value) / previous_value, 1)
             AS growth_pct
    FROM streaks
    WHERE increased = 1
      AND customer_id IN (SELECT customer_id FROM qualifying)
    ORDER BY customer_name, month
"""

# Q3: running revenue by order date across all counties.
# Interpretation: revenue passed KES 1 million on 8 October and closed the
# quarter at KES 1,569,550, but two bulk rice orders in October added
# KES 288,000 between them, so growth is lumpy rather than steady.
Q3_RUNNING_TOTAL = """
    WITH daily AS (
        SELECT order_date,
               SUM(quantity * unit_price) AS daily_revenue
        FROM orders
        WHERE status <> 'cancelled'
        GROUP BY order_date
    )
    SELECT order_date,
           daily_revenue,
           SUM(daily_revenue) OVER (
               ORDER BY order_date
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS running_total
    FROM daily
    ORDER BY order_date
"""

Q1_LABELS = {
    "county": "County",
    "total_orders": "Orders",
    "completed": "Completed",
    "pending": "Pending",
    "cancelled": "Cancelled",
    "completed_pct": "Completed %",
    "pending_pct": "Pending %",
    "cancelled_pct": "Cancelled %",
}

Q2_LABELS = {
    "customer_name": "Customer",
    "county": "County",
    "month": "Month",
    "previous_month": "Previous month",
    "previous_value": "Previous (KES)",
    "month_value": "Month (KES)",
    "growth_value": "Growth (KES)",
    "growth_pct": "Growth %",
}

Q3_LABELS = {
    "order_date": "Date",
    "daily_revenue": "Daily revenue (KES)",
    "running_total": "Running total (KES)",
}

# Bonus: HAVING filters groups after aggregation, which is how a board gets a
# threshold list rather than a full table. Cancellation is measured on the
# exact fraction, not the rounded percentage, so 10.04% still counts as over.
BONUS_CANCELLATION_THRESHOLD = """
    SELECT c.county,
           COUNT(*) AS total_orders,
           SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
           ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS cancelled_pct
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.county
    HAVING 1.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
           / COUNT(*) > 0.10
    ORDER BY cancelled_pct DESC, c.county
"""

BONUS_LABELS = {
    "county": "County",
    "total_orders": "Orders",
    "cancelled": "Cancelled",
    "cancelled_pct": "Cancelled %",
}


class DataError(Exception):
    """Raised when the database can't be used, with a message a manager understands."""


def open_database(path):
    if not path.exists():
        raise DataError(f"Can't find {path}. Run generate_analytical_data.py first.")

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        customers, orders = conn.execute(
            "SELECT (SELECT COUNT(*) FROM customers), COUNT(*) FROM orders"
        ).fetchone()
    except sqlite3.Error as error:
        if "conn" in locals():
            conn.close()
        raise DataError(f"{path.name} needs both a customers and an orders table "
                        f"({error}). Run generate_analytical_data.py again.")

    if customers == 0 or orders == 0:
        conn.close()
        raise DataError(f"The database has {customers} customers and {orders} orders. "
                        f"Run generate_analytical_data.py to rebuild it.")

    return conn


def money(value):
    return f"{value:,.0f}"


def print_table(title, df, labels):
    print(title)
    table = df.rename(columns=labels)

    for column in table.columns:
        if column.endswith("(KES)"):
            table[column] = table[column].map(money)
        elif column.endswith(" %"):
            table[column] = table[column].map(lambda value: f"{value:.1f}")
        elif column == "Orders":
            table[column] = table[column].map(lambda value: f"{value:,}")

    print(table.to_string(index=False))
    print()


def plan_details(conn):
    rows = conn.execute(
        "EXPLAIN QUERY PLAN "
        "SELECT customer_id, customer_name FROM customers WHERE county = ?",
        ("Mombasa",),
    ).fetchall()
    return [row[3].strip() for row in rows]


def main():
    try:
        conn = open_database(DB_PATH)

        print("Nairobi Wholesale Distributor: analytical queries for the board")
        print(f"Database: {DB_PATH}\n")

        status_mix = pd.read_sql_query(Q1_STATUS_MIX, conn)
        print_table("Q1. Order status mix by county  (completed, pending, cancelled)",
                    status_mix, Q1_LABELS)

        growth = pd.read_sql_query(Q2_MONTH_ON_MONTH, conn)
        if growth.empty:
            print("Q2. No customer grew in two consecutive months.\n")
        else:
            print_table("Q2. Customers growing in two consecutive months  (LAG)",
                        growth, Q2_LABELS)

        running = pd.read_sql_query(Q3_RUNNING_TOTAL, conn)
        print_table("Q3. Running revenue by date across all counties",
                    running, Q3_LABELS)

        threshold = pd.read_sql_query(BONUS_CANCELLATION_THRESHOLD, conn)
        print_table("Bonus. Counties with more than 10% of orders cancelled  (HAVING)",
                    threshold, BONUS_LABELS)

        print("Query plan check for a county filter")
        for detail in plan_details(conn):
            print(f"  {detail}")
    except DataError as error:
        sys.exit(f"Can't build the analysis. {error}")
    except sqlite3.Error as error:
        sys.exit(f"Can't build the analysis. A query failed: {error}")
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
