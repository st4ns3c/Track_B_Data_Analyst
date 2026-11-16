"""
Nairobi wholesale distributor: joins and subqueries
---------------------------------------------------
Build plan
  Problem : the sales manager wants to know which customers drive revenue and
            whether the best customers cluster in one county. That needs data
            from both the customers and orders tables.
  Input   : data/distributor.db, built by generate_data.py.
  Output  : the three exercise queries plus one LEFT JOIN check, printed with
            pandas read_sql_query.

Usage:
    python generate_data.py
    python queries.py

Requirements:
    pip install pandas
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "distributor.db"
MIN_CUSTOMERS = 10
MIN_ORDERS = 30

COLUMN_LABELS = {
    "order_id": "Order",
    "customer_name": "Customer",
    "account_tier": "Tier",
    "product": "Product",
    "order_date": "Date",
    "order_value": "Value (KES)",
    "status": "Status",
    "county": "County",
    "order_count": "Orders",
    "total_spend": "Total spend (KES)",
    "avg_order": "Avg order (KES)",
}


def answer_q1(df, context):
    if df.empty:
        return "No orders matched a customer."
    top = df.loc[df["order_value"].idxmax()]
    return (f"{len(df)} of {context['orders']} orders matched a customer. The "
            f"largest is {top['customer_name']} at KES {top['order_value']:,.0f}.")


def answer_q2(df, _context):
    if df.empty:
        return "No customer has placed more than three orders."
    top = df.iloc[0]
    return (f"{len(df)} customers have placed more than three orders. "
            f"{top['customer_name']} leads with KES {top['total_spend']:,.0f} "
            f"from {top['order_count']} orders.")


def answer_q3(df, _context):
    if df.empty:
        return "No county has a customer with orders."
    top = df.iloc[0]
    return (f"{len(df)} counties have a top customer. {top['customer_name']} "
            f"({top['county']}) is the biggest single account at "
            f"KES {top['total_spend']:,.0f}.")


QUERIES = [
    {
        "number": 1,
        "question": "Every order with the customer's account tier",
        "sql": """
            SELECT o.order_id,
                   c.customer_name,
                   c.account_tier,
                   o.product,
                   o.order_date,
                   o.quantity * o.unit_price AS order_value,
                   o.status
            FROM orders o
            INNER JOIN customers c ON o.customer_id = c.customer_id
            ORDER BY o.order_id
        """,
        "answer": answer_q1,
    },
    {
        "number": 2,
        "question": "Total spend per customer, only customers with more than three orders",
        "sql": """
            SELECT c.customer_name,
                   c.county,
                   c.account_tier,
                   COUNT(o.order_id) AS order_count,
                   SUM(o.quantity * o.unit_price) AS total_spend,
                   ROUND(AVG(o.quantity * o.unit_price), 0) AS avg_order
            FROM customers c
            INNER JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id, c.customer_name, c.county, c.account_tier
            HAVING COUNT(o.order_id) > 3
            ORDER BY total_spend DESC
        """,
        "answer": answer_q2,
    },
    {
        "number": 3,
        "question": "The top customer in each county",
        "sql": """
            WITH customer_totals AS (
                SELECT c.customer_id,
                       c.customer_name,
                       c.county,
                       c.account_tier,
                       COUNT(o.order_id) AS order_count,
                       SUM(o.quantity * o.unit_price) AS total_spend
                FROM customers c
                INNER JOIN orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id, c.customer_name, c.county, c.account_tier
            )
            SELECT county, customer_name, account_tier, order_count, total_spend
            FROM customer_totals ct
            WHERE total_spend = (
                SELECT MAX(total_spend)
                FROM customer_totals
                WHERE county = ct.county
            )
            ORDER BY total_spend DESC
        """,
        "answer": answer_q3,
    },
]

BONUS_QUERY = {
    "question": "Bonus: customers who have never placed an order (LEFT JOIN)",
    "sql": """
        SELECT c.customer_name, c.county, c.account_tier
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_id IS NULL
        ORDER BY c.customer_name
    """,
}


class DataError(Exception):
    """Raised when the database can't be used, with a message a manager understands."""


def open_database(path):
    if not path.exists():
        raise DataError(f"Can't find {path}. Run generate_data.py first.")

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as error:
        raise DataError(f"{path.name} is not a usable database ({error}). "
                        f"Run generate_data.py again.")

    try:
        customers, orders = conn.execute(
            "SELECT (SELECT COUNT(*) FROM customers), COUNT(*) FROM orders"
        ).fetchone()
        broken_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    except sqlite3.Error as error:
        conn.close()
        raise DataError(f"{path.name} needs both a customers and an orders table "
                        f"({error}). Run generate_data.py again.")

    if customers < MIN_CUSTOMERS or orders < MIN_ORDERS:
        conn.close()
        raise DataError(f"The database has {customers} customers and {orders} orders. "
                        f"Run generate_data.py to rebuild it.")
    if broken_keys:
        conn.close()
        raise DataError("Some orders point to a customer that is not in the customers "
                        "table. Run generate_data.py to rebuild the database.")

    return conn, customers, orders


def print_table(df):
    table = df.rename(columns=COLUMN_LABELS)

    for column in table.columns:
        if column.endswith("(KES)"):
            table[column] = table[column].map(lambda value: f"{value:,.0f}")
        elif column in ("Orders",):
            table[column] = table[column].map(lambda value: f"{value:,}")

    print(table.to_string(index=False))


def bonus_answer(df):
    if df.empty:
        return "Every customer has placed at least one order."

    details = ", ".join(
        f"{row.customer_name} ({row.account_tier}, {row.county})"
        for row in df.itertuples()
    )
    verb = "has" if len(df) == 1 else "have"
    return (f"{len(df)} customer{'' if len(df) == 1 else 's'} {verb} never "
            f"ordered: {details}. That is the first sales call.")


def main():
    try:
        conn, customers, orders = open_database(DB_PATH)
        context = {"customers": customers, "orders": orders}

        print("Nairobi Wholesale Distributor: customers, revenue and counties")
        print(f"Database: {DB_PATH}  ·  {customers} customers  ·  {orders} orders\n")

        for query in QUERIES:
            df = pd.read_sql_query(query["sql"], conn)
            rows = f"{len(df)} row{'s' if len(df) != 1 else ''} returned"
            print(f"Q{query['number']}. {query['question']}  ({rows})")
            print_table(df)
            print(f"Answer: {query['answer'](df, context)}\n")

        bonus = pd.read_sql_query(BONUS_QUERY["sql"], conn)
        print(f"{BONUS_QUERY['question']}  ({len(bonus)} row"
              f"{'s' if len(bonus) != 1 else ''} returned)")
        print_table(bonus)
        print(f"Answer: {bonus_answer(bonus)}")
    except DataError as error:
        sys.exit(f"Can't complete the report. {error}")
    except sqlite3.Error as error:
        sys.exit(f"Can't complete the report. The query failed: {error}")
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
