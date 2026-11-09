"""
Supermarket Foot Traffic: monthly trend and 30-day average
-----------------------------------------------------------
Build plan
  Problem : a Nairobi supermarket chain wants to know whether foot traffic is
            genuinely growing or just following the seasons.
  Input   : data/daily_transactions.csv (date, transactions).
  Processing : turn the dates into the index, total the daily counts by month,
               and smooth the daily counts with a 30-day rolling average. Then
               plot both on one chart.
  Output  : traffic_trend.png for the operations manager, and a short summary
            on screen for whoever runs the script.

Usage:
    python traffic_trend.py
    python traffic_trend.py path/to/daily_transactions.csv

Requirements:
    pip install pandas matplotlib
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).parent
DEFAULT_DATA = BASE_DIR / "data" / "daily_transactions.csv"
CHART_PATH = BASE_DIR / "traffic_trend.png"

WINDOW = 30


class DataError(Exception):
    """Raised when the input can't be used, with a message a manager understands."""


def load_data(path):
    """Read the CSV, check the columns, and make the date the index."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}. Run generate_sample_data.py first.")

    missing = {"date", "transactions"} - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): "
                        f"{', '.join(sorted(missing))}. Expected: date, transactions.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        raise DataError(f"{bad_dates} row(s) have a date that isn't a real date. "
                        f"Use the format 2026-05-31.")

    df = df.dropna(subset=["transactions"])
    df = df.sort_values("date").drop_duplicates("date", keep="last")
    return df.set_index("date")


def build_summary(daily):
    """Monthly totals and the 30-day rolling average, both as Series."""
    monthly = daily["transactions"].resample("MS").sum()
    rolling = daily["transactions"].rolling(WINDOW, min_periods=WINDOW).mean()
    return monthly, rolling


def plot_trend(daily, monthly, rolling):
    """Bar chart of monthly totals with the 30-day average drawn over it."""
    fig, ax = plt.subplots(figsize=(12, 6.5))

    bars = ax.bar(
        monthly.index, monthly.values, width=24,
        color="#9DC3E6", edgecolor="#2E75B6", linewidth=0.8,
        label="Monthly total (bars, left axis)",
    )
    ax.set_ylabel("Transactions in the month")
    ax.set_xlabel("Month")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_ylim(0, monthly.max() * 1.14)

    # The daily average lives on a different scale from the monthly total, so
    # it gets its own axis on the right.
    ax2 = ax.twinx()
    line, = ax2.plot(
        rolling.index, rolling.values, color="#C00000", linewidth=2.2,
        label=f"{WINDOW}-day average, per day (line, right axis)",
    )
    ax2.set_ylabel("Average transactions per day")
    ax2.set_ylim(rolling.min() * 0.88, rolling.max() * 1.08)

    fig.suptitle("Nairobi Supermarket: Foot Traffic, December 2024 to May 2026",
                 fontsize=15, y=0.985)
    fig.text(0.5, 0.925,
             "Is the store getting busier, or is it just the Christmas rush?",
             ha="center", fontsize=10.5, color="#444444")

    # Point out the two seasons a manager would ask about.
    for label, when in [
        ("December peak", "2025-12-01"),
        ("February dip", "2026-02-01"),
    ]:
        stamp = pd.Timestamp(when)
        if stamp in monthly.index:
            ax.annotate(
                label,
                xy=(stamp, monthly.loc[stamp]),
                xytext=(0, 8), textcoords="offset points",
                ha="center", va="bottom", fontsize=9.5, color="#1F4E79",
            )

    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 3, 5, 7, 9, 11]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    ax.legend(handles=[bars, line], loc="upper left", frameon=False, fontsize=9.5)

    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def print_summary(daily, monthly):
    """The numbers behind the chart, in the order a manager would ask for them."""
    best = monthly.idxmax()
    worst = monthly.idxmin()

    feb = daily[daily.index.month == 2]["transactions"].mean()
    dec = daily[daily.index.month == 12]["transactions"].mean()

    # The first and last six months cover the same calendar months
    # (December to May), so the seasons cancel out and the difference is trend.
    first_six = daily["transactions"].iloc[:182].mean()
    last_six = daily["transactions"].iloc[-182:].mean()

    print(f"Period covered      : {daily.index.min():%d %b %Y} to {daily.index.max():%d %b %Y}"
          f" ({len(daily):,} days)")
    print(f"Total transactions  : {daily['transactions'].sum():,}")

    print("\nMonthly totals")
    print(f"  {'Month':<10}{'Transactions':>14}{'Change on previous':>22}")
    previous = None
    for stamp, total in monthly.items():
        change = "" if previous is None else f"{(total / previous - 1) * 100:+.1f}%"
        print(f"  {stamp:%b %Y}    {total:>14,}{change:>22}")
        previous = total

    print(f"\nBusiest month       : {best:%B %Y} ({monthly.loc[best]:,} transactions)")
    print(f"Quietest month      : {worst:%B %Y} ({monthly.loc[worst]:,} transactions)")
    print(f"Average December day: {dec:,.0f} transactions")
    print(f"Average February day: {feb:,.0f} transactions")
    print(f"Dec-May 2024/25     : {first_six:,.0f} a day")
    print(f"Dec-May 2025/26     : {last_six:,.0f} a day ({(last_six / first_six - 1) * 100:+.1f}%)")

    # Same month, one year apart: this is what separates growth from season.
    for month_name, month_number in [("December", 12), ("February", 2)]:
        years = [y for y in sorted(daily.index.year.unique())
                 if len(daily[(daily.index.year == y) & (daily.index.month == month_number)]) >= 28]
        if len(years) == 2:
            current = daily[(daily.index.year == years[1]) & (daily.index.month == month_number)]["transactions"].mean()
            before = daily[(daily.index.year == years[0]) & (daily.index.month == month_number)]["transactions"].mean()
            print(f"{month_name} {years[0]} vs {years[1]}  : {before:,.0f} to {current:,.0f} a day "
                  f"({(current / before - 1) * 100:+.1f}%)")


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    try:
        daily = load_data(data_path)
        monthly, rolling = build_summary(daily)
        plot_trend(daily, monthly, rolling)
        print_summary(daily, monthly)
    except DataError as error:
        sys.exit(f"Can't build the chart. {error}")

    print(f"\nChart saved: {CHART_PATH.name}")


if __name__ == "__main__":
    main()
