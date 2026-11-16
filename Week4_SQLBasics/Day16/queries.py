"""
Nairobi wholesale distributor: the five Monday-morning questions
-----------------------------------------------------------------
Build plan
  Problem : the sales manager spends about 45 minutes each Monday pulling five
            answers out of Excel by hand.
  Input   : data/orders.db, built by generate_orders.py.
  Output  : five result tables and a one-line answer for each question, printed
            to the screen with pandas read_sql_query.

Usage:
    python generate_orders.py
    python queries.py

Requirements:
    pip install pandas
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "orders.db"
MIN_ORDERS = 20

COLUMN_LABELS = {
    "order_id": "Order",
    "customer_name": "Customer",
    "county": "County",
    "product": "Product",
    "quantity": "Qty",
    "unit_price": "Unit price (KES)",
    "total_value": "Total (KES)",
    "order_date": "Date",
    "status": "Status",
    "order_count": "Orders",
    "total_revenue": "Revenue (KES)",
    "avg_order_value": "Avg order (KES)",
    "total_units": "Units",
}

QUERIES = [
    {
        "number": 1,
        "question": "All orders from Mombasa county",
        "sql": """
            SELECT order_id, customer_name, product, quantity, unit_price,
                   quantity * unit_price AS total_value, order_date, status
            FROM orders
            WHERE county = 'Mombasa'
            ORDER BY order_date, order_id
        """,
        "answer": lambda df, overall: (
            f"{len(df)} orders came from Mombasa, worth "
            f"KES {df['total_value'].sum():,.0f} in total."
        ),
    },
    {
        "number": 2,
        "question": "Top 10 orders by total value",
        "sql": """
            SELECT order_id, customer_name, county, product, quantity,
                   quantity * unit_price AS total_value, order_date
            FROM orders
            ORDER BY total_value DESC, order_id
            LIMIT 10
        """,
        "answer": lambda df, overall: (
            f"The ten largest orders are worth KES {df['total_value'].sum():,.0f}, "
            f"{df['total_value'].sum() / overall:.0%} of all revenue. The biggest is "
            f"{df.iloc[0]['customer_name']} at KES {df.iloc[0]['total_value']:,.0f}."
        ),
    },
    {
        "number": 3,
        "question": "Total revenue per county",
        "sql": """
            SELECT county,
                   COUNT(*) AS order_count,
                   SUM(quantity * unit_price) AS total_revenue,
                   ROUND(AVG(quantity * unit_price), 0) AS avg_order_value
            FROM orders
            GROUP BY county
            ORDER BY total_revenue DESC
        """,
        "answer": lambda df, overall: (
            f"{df.iloc[0]['county']} leads with KES "
            f"{df.iloc[0]['total_revenue']:,.0f} from "
            f"{df.iloc[0]['order_count']} orders. {len(df)} counties are represented."
        ),
    },
    {
        "number": 4,
        "question": "Pending orders over KES 50,000",
        "sql": """
            SELECT order_id, customer_name, county, product,
                   quantity * unit_price AS total_value, order_date
            FROM orders
            WHERE status = 'pending'
              AND quantity * unit_price > 50000
            ORDER BY total_value DESC, order_id
        """,
        "answer": lambda df, overall: (
            f"{len(df)} pending orders are over KES 50,000, worth "
            f"KES {df['total_value'].sum():,.0f}. They are still waiting to ship."
        ),
    },
    {
        "number": 5,
        "question": "The three best-selling products by quantity",
        "sql": """
            SELECT product,
                   COUNT(*) AS order_count,
                   SUM(quantity) AS total_units,
                   SUM(quantity * unit_price) AS total_revenue
            FROM orders
            GROUP BY product
            ORDER BY total_units DESC, product
            LIMIT 3
        """,
        "answer": lambda df, overall: (
            f"{df.iloc[0]['product']} sells the most units "
            f"({df.iloc[0]['total_units']:,}), ahead of "
            f"{df.iloc[1]['product']} ({df.iloc[1]['total_units']:,}) and "
            f"{df.iloc[2]['product']} ({df.iloc[2]['total_units']:,}). "
            f"{df.loc[df['total_revenue'].idxmax(), 'product']} earns the most revenue "
            f"of these three (KES {df['total_revenue'].max():,.0f})."
        ),
    },
]


class DataError(Exception):
    """Raised when the database can't be used, with a message a manager understands."""


def open_database(path):
    if not path.exists():
        raise DataError(f"Can't find {path}. Run generate_orders.py first.")

    try:
        # Read-only: the reporting script should never change the orders.
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as error:
        raise DataError(f"{path.name} is not a usable orders database ({error}). "
                        f"Run generate_orders.py again.")

    try:
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    except sqlite3.Error as error:
        conn.close()
        raise DataError(f"{path.name} is not a usable orders database ({error}). "
                        f"Run generate_orders.py again.")

    if count < MIN_ORDERS:
        conn.close()
        raise DataError(f"The orders table has only {count} rows. "
                        f"Run generate_orders.py to rebuild it.")

    return conn, count


def overall_revenue(conn):
    return conn.execute(
        "SELECT SUM(quantity * unit_price) FROM orders"
    ).fetchone()[0]


def print_table(df):
    table = df.rename(columns=COLUMN_LABELS)

    for column in table.columns:
        if column.endswith("(KES)"):
            table[column] = table[column].map(lambda value: f"{value:,.0f}")
        elif column in ("Qty", "Orders", "Units"):
            table[column] = table[column].map(lambda value: f"{value:,}")

    print(table.to_string(index=False))


def main():
    try:
        conn, count = open_database(DB_PATH)
        total = overall_revenue(conn)

        print(f"Nairobi Wholesale Distributor: Monday morning questions")
        print(f"Database: {DB_PATH}  ·  {count} orders  ·  "
              f"Total value: KES {total:,.0f}\n")

        for query in QUERIES:
            df = pd.read_sql_query(query["sql"], conn)
            rows = f"{len(df)} row{'s' if len(df) != 1 else ''} returned"
            print(f"Q{query['number']}. {query['question']}  ({rows})")
            print_table(df)
            print(f"Answer: {query['answer'](df, total)}\n")
    except DataError as error:
        sys.exit(f"Can't complete the report. {error}")
    except sqlite3.Error as error:
        sys.exit(f"Can't complete the report. The query failed: {error}")
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
