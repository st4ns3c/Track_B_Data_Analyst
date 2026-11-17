"""
Wanjiru's Cafe: sample M-Pesa business statement
------------------------------------------------
Build plan
  Problem : a small cafe on Thika Road takes most of its sales on an
            M-Pesa till. The owner wants to see daily takings, where the
            money goes, and the weekly trend without reading the statement
            line by line.
  Input   : none. This script makes the data.
  Output  : data/mpesa_statement.csv, laid out like an M-Pesa business
            statement export: Receipt No., Completion Time, Details,
            Transaction Status, Reason Type, Paid In, Withdrawn, Balance.

The columns are modelled on the statement a business downloads from
M-Pesa, not copied from a real one. Phone numbers are masked and every
name is made up. The seed is fixed (2525), so every run writes the same
statement: Tuesday 15 September to Saturday 14 November 2026.

What the dashboard should be able to see:
  - Customer payments every day, busiest at breakfast and lunch, quieter on
    Sundays, with a lift after month-end pay days.
  - A small merchant charge on every customer payment.
  - Money going out to suppliers, weekly wages, electricity tokens, and a
    sweep to the bank whenever the till balance runs high.
  - A few failed payments and the odd reversal, which must not be counted
    as sales.

Usage:
    python generate_mpesa_statement.py

Requirements:
    pip install numpy pandas
"""

import string
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "mpesa_statement.csv"

SEED = 2525
START = date(2026, 9, 15)
END = date(2026, 11, 14)
OPENING_BALANCE = 18_500
MERCHANT_RATE = 0.0055        # charge on each customer payment
BANK_SWEEP_ABOVE = 60_000     # move money to the bank when the till holds more
KEEP_IN_TILL = 15_000

FIRST_NAMES = ["JOHN", "MARY", "PETER", "GRACE", "JAMES", "FAITH", "DAVID", "MERCY",
               "BRIAN", "JOY", "KEVIN", "ANN", "DENNIS", "LUCY", "SAMUEL", "ESTHER",
               "MICHAEL", "IRENE", "GEORGE", "SHARON", "PAUL", "CAROLINE", "MOSES", "JANE"]
SUPPLIERS = [("400210", "Fresh Milk Distributors", "WC001"),
             ("400355", "Mkate Bakery Supplies", "WC014"),
             ("400478", "Green Grocers Wholesale", "CAFE22"),
             ("400512", "Highland Coffee Traders", "WCAFE")]
STAFF = ["MARY W", "KEVIN O", "ANN M", "SAMUEL K"]

# Share of the day's customer payments in each opening hour (06:00-20:00).
HOUR_WEIGHTS = np.array([2, 8, 9, 6, 4, 5, 10, 11, 7, 4, 4, 6, 7, 5, 2], dtype=float)
HOURS = np.arange(6, 21)


def receipt(rng):
    letters = string.ascii_uppercase + string.digits
    return "T" + "".join(rng.choice(list(letters), size=9))


def masked_phone(rng):
    return f"2547******{rng.integers(100, 999)}"


def customer_count(day, rng):
    base = 95
    if day.weekday() == 5:
        base *= 1.15          # Saturday
    if day.weekday() == 6:
        base *= 0.55          # Sunday: shorter hours
    if day.day >= 28 or day.day <= 3:
        base *= 1.2           # pay days
    base *= 1 + 0.10 * (day - START).days / (END - START).days
    return int(rng.poisson(base))


def build_events(rng):
    """Every movement of money, before the running balance is added."""
    events = []
    day = START
    while day <= END:
        # Customer payments, each with its merchant charge a second later.
        for _ in range(customer_count(day, rng)):
            hour = int(rng.choice(HOURS, p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum()))
            when = datetime(day.year, day.month, day.day, hour, int(rng.integers(0, 60)),
                            int(rng.integers(0, 60)))
            amount = int(max(50, round(rng.lognormal(np.log(320), 0.55) / 10) * 10))
            who = f"{masked_phone(rng)} - {rng.choice(FIRST_NAMES)} {rng.choice(list('ABCDEGHJKMNOW'))}"
            if rng.random() < 0.015:
                events.append((when, f"Payment from {who}", "Failed", "Customer Payment", 0, 0))
                continue
            events.append((when, f"Payment from {who}", "Completed", "Customer Payment", amount, 0))
            charge = round(amount * MERCHANT_RATE, 2)
            events.append((when + timedelta(seconds=1), "Merchant Payment Charge", "Completed",
                           "Merchant Charge", 0, charge))
            if rng.random() < 0.004:
                events.append((when + timedelta(minutes=int(rng.integers(5, 40))),
                               f"Reversal to {who}", "Completed", "Reversal", 0, amount))

        # Suppliers on Monday, Wednesday and Friday mornings.
        if day.weekday() in (0, 2, 4):
            for code, name, account in rng.choice(SUPPLIERS, size=2, replace=False):
                amount = int(round(rng.lognormal(np.log(6500), 0.3), -1))
                when = datetime(day.year, day.month, day.day, 9, int(rng.integers(0, 59)))
                events.append((when, f"Pay Bill to {code} - {name} Acc. {account}", "Completed",
                               "Supplier Payment", 0, amount))
        # Weekly wages on Saturday evening.
        if day.weekday() == 5:
            for person in STAFF:
                when = datetime(day.year, day.month, day.day, 19, int(rng.integers(0, 59)))
                events.append((when, f"Salary Payment to {masked_phone(rng)} - {person}", "Completed",
                               "Salary Payment", 0, 3500))
        # Electricity tokens every Tuesday.
        if day.weekday() == 1:
            when = datetime(day.year, day.month, day.day, 8, 15)
            events.append((when, "Pay Bill to 400999 - Electricity Tokens Acc. ****7731", "Completed",
                           "Utility Payment", 0, int(rng.choice([1500, 2000, 2500]))))
        day += timedelta(days=1)
    return sorted(events, key=lambda e: e[0])


def add_balance_and_sweeps(events, rng):
    rows, balance = [], OPENING_BALANCE
    last_day = None
    for when, details, status, reason, paid_in, withdrawn in events:
        # End of each trading day: sweep the till to the bank if it runs high.
        if last_day and when.date() != last_day and balance > BANK_SWEEP_ABOVE:
            amount = int((balance - KEEP_IN_TILL) // 1000 * 1000)
            # After closing: the last payments of the day come in before 21:00.
            sweep_time = datetime.combine(last_day, datetime.min.time()) + timedelta(hours=21, minutes=10)
            balance -= amount
            rows.append((receipt(rng), sweep_time, "Withdraw to Bank - Cafe Account ****4521",
                         "Completed", "Bank Transfer", 0, amount, round(balance, 2)))
        last_day = when.date()
        if status == "Completed":
            balance += paid_in - withdrawn
        rows.append((receipt(rng), when, details, status, reason, paid_in, withdrawn, round(balance, 2)))
    df = pd.DataFrame(rows, columns=["Receipt No.", "Completion Time", "Details", "Transaction Status",
                                     "Reason Type", "Paid In", "Withdrawn", "Balance"])
    df["Completion Time"] = pd.to_datetime(df["Completion Time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    # Statements list the newest transaction first.
    return df.iloc[::-1].reset_index(drop=True)


def main():
    rng = np.random.default_rng(SEED)
    df = add_balance_and_sweeps(build_events(rng), rng)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)

    done = df[df["Transaction Status"] == "Completed"]
    sales = done[done["Reason Type"] == "Customer Payment"]
    print(f"Wrote {len(df):,} transactions to {CSV_PATH}")
    print(f"Period: {df['Completion Time'].min()[:10]} to {df['Completion Time'].max()[:10]}")
    print(f"Customer payments: {len(sales):,} worth KES {sales['Paid In'].sum():,.0f}")
    print(f"Money out: KES {done['Withdrawn'].sum():,.0f}; closing balance KES {df['Balance'].iloc[0]:,.2f}")


if __name__ == "__main__":
    main()
