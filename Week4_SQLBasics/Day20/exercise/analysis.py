"""
Kisumu fish market: sponsor report on the first three months
------------------------------------------------------------
Build plan
  Problem : the fish market association needs a printable report for its
            county government sponsor that answers three questions with data:
              1. Which three vendors generated the most revenue?
              2. Is wholesale or retail more profitable per kg on average?
              3. Is total revenue trending up, flat or down?
  Input   : data/fish_market.db, built by generate_fish_market_data.py.
  Processing : SQL does the grouping and totals; pandas adds shares, the
               weekly trend line and the up/flat/down verdict.
  Output  : the three answers on screen, charts/weekly_revenue.png, and
            report.md, the sponsor report with three findings and one
            recommendation.

Usage:
    python generate_fish_market_data.py
    python analysis.py

Requirements:
    pip install pandas numpy matplotlib
"""

import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "fish_market.db"
CHART_PATH = BASE_DIR / "charts" / "weekly_revenue.png"
REPORT_PATH = BASE_DIR / "report.md"

REQUIRED_COLUMNS = {"sale_date", "vendor", "fish_type", "kg_sold",
                    "price_per_kg", "buyer_type"}

# A fitted line that moves less than 10% of the average week over the quarter
# is within normal week-to-week noise for a market this size, so it is "flat".
FLAT_BAND_PCT = 10

Q1_TOP_VENDORS = """
    SELECT vendor,
           COUNT(*) AS sales,
           ROUND(SUM(kg_sold), 1) AS kg_sold,
           ROUND(SUM(kg_sold * price_per_kg)) AS revenue_kes,
           ROUND(100.0 * SUM(CASE WHEN buyer_type = 'wholesale'
                                  THEN kg_sold * price_per_kg ELSE 0 END)
                 / SUM(kg_sold * price_per_kg), 1) AS wholesale_pct
    FROM sales
    GROUP BY vendor
    ORDER BY revenue_kes DESC
"""

# Revenue per kg is weighted by the kilograms sold: SUM(revenue) / SUM(kg).
# A plain AVG(price_per_kg) would count a 2 kg sale the same as a 90 kg one.
Q2_BUYER_TYPE = """
    SELECT buyer_type,
           COUNT(*) AS sales,
           ROUND(SUM(kg_sold), 1) AS kg_sold,
           ROUND(SUM(kg_sold * price_per_kg)) AS revenue_kes,
           ROUND(SUM(kg_sold * price_per_kg) / SUM(kg_sold), 1) AS kes_per_kg,
           ROUND(AVG(price_per_kg), 1) AS simple_avg_price,
           ROUND(AVG(kg_sold), 1) AS avg_kg_per_sale
    FROM sales
    GROUP BY buyer_type
    ORDER BY kes_per_kg DESC
"""

# The same comparison inside each fish type, so a retail premium cannot be
# explained away by retail buyers simply choosing more expensive fish.
Q2_BY_FISH = """
    SELECT fish_type,
           ROUND(SUM(CASE WHEN buyer_type = 'retail'
                          THEN kg_sold * price_per_kg END)
                 / SUM(CASE WHEN buyer_type = 'retail' THEN kg_sold END), 1)
             AS retail_kes_per_kg,
           ROUND(SUM(CASE WHEN buyer_type = 'wholesale'
                          THEN kg_sold * price_per_kg END)
                 / SUM(CASE WHEN buyer_type = 'wholesale' THEN kg_sold END), 1)
             AS wholesale_kes_per_kg
    FROM sales
    GROUP BY fish_type
    ORDER BY fish_type
"""

# Weeks start on Monday: date(d, 'weekday 0', '-6 days') moves forward to the
# next Sunday (or stays on a Sunday) and steps back six days.
Q3_WEEKLY = """
    SELECT date(sale_date, 'weekday 0', '-6 days') AS week_start,
           COUNT(*) AS sales,
           ROUND(SUM(kg_sold * price_per_kg)) AS revenue_kes
    FROM sales
    GROUP BY week_start
    ORDER BY week_start
"""

# Months have different numbers of selling days, so revenue per day with sales
# is the fair month-to-month comparison. LAG brings last month onto this row.
Q3_MONTHLY = """
    WITH monthly AS (
        SELECT strftime('%Y-%m', sale_date) AS month,
               COUNT(DISTINCT sale_date) AS days_with_sales,
               ROUND(SUM(kg_sold * price_per_kg)) AS revenue_kes
        FROM sales
        GROUP BY month
    )
    SELECT month,
           days_with_sales,
           revenue_kes,
           ROUND(revenue_kes / days_with_sales) AS revenue_per_day,
           ROUND(100.0 * (revenue_kes - LAG(revenue_kes) OVER (ORDER BY month))
                 / LAG(revenue_kes) OVER (ORDER BY month), 1) AS change_pct
    FROM monthly
    ORDER BY month
"""


class ReportError(Exception):
    """Raised when the report can't be built, with a message a client understands."""


def connect():
    """Open the database read-only; the report must never change the records."""
    if not DB_PATH.exists():
        raise ReportError(
            f"Can't find the sales database at {DB_PATH}. "
            "Run generate_fish_market_data.py first."
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sales)")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        conn.close()
        raise ReportError(
            "The sales table is missing these columns: "
            + ", ".join(sorted(missing))
            + ". Rebuild it with generate_fish_market_data.py."
        )
    bad_dates = conn.execute(
        "SELECT COUNT(*) FROM sales WHERE date(sale_date) IS NULL"
    ).fetchone()[0]
    if bad_dates:
        conn.close()
        raise ReportError(
            f"{bad_dates} sale(s) have a date that is not a real date "
            "(expected YYYY-MM-DD). Correct them before running the report."
        )
    if conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        conn.close()
        raise ReportError("The sales table is empty, so there is nothing to report.")
    return conn


def classify_trend(weekly):
    """Fit a straight line through weekly revenue and call it up, flat or down."""
    x = np.arange(len(weekly))
    slope, intercept = np.polyfit(x, weekly["revenue_kes"], 1)
    fitted = intercept + slope * x
    change_pct = (fitted[-1] - fitted[0]) / weekly["revenue_kes"].mean() * 100
    if change_pct > FLAT_BAND_PCT:
        verdict = "up"
    elif change_pct < -FLAT_BAND_PCT:
        verdict = "down"
    else:
        verdict = "flat"
    return fitted, slope, change_pct, verdict


def plot_weekly(weekly, fitted, verdict, change_pct):
    CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5.5))

    labels = weekly["week_start"].dt.strftime("%d %b")
    ax.bar(labels, weekly["revenue_kes"], color="#2E75B6", label="Weekly revenue")
    ax.plot(labels, fitted, color="#C00000", linewidth=2.5,
            label=f"Trend line ({change_pct:+.0f}% over the quarter)")

    ax.set_title(f"Kisumu fish market: weekly revenue is trending {verdict}, "
                 "Aug to Oct 2026", fontsize=13, fontweight="bold")
    ax.set_xlabel("Week starting (Monday)")
    ax.set_ylabel("Revenue (KES)")
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def count_word(n):
    words = ["no", "one", "two", "three", "four", "five", "six", "seven",
             "eight", "nine", "ten"]
    return words[n] if n < len(words) else str(n)


def kes(value):
    return f"KES {value:,.0f}"


def write_report(vendors, buyers, by_fish, monthly, weekly, change_pct, verdict):
    total = vendors["revenue_kes"].sum()
    top3 = vendors.head(3)
    top3_share = top3["revenue_kes"].sum() / total * 100
    names = ", ".join(
        f"{row.vendor} ({kes(row.revenue_kes)})" for row in top3.itertuples()
    )

    retail = buyers.set_index("buyer_type").loc["retail"]
    wholesale = buyers.set_index("buyer_type").loc["wholesale"]
    premium = (retail["kes_per_kg"] / wholesale["kes_per_kg"] - 1) * 100
    wholesale_share = wholesale["revenue_kes"] / total * 100
    low, high = by_fish["retail_premium_pct"].min(), by_fish["retail_premium_pct"].max()

    others = vendors.iloc[3:]
    others_share = others["revenue_kes"].sum() / total * 100
    top3_wholesale = (top3["revenue_kes"] * top3["wholesale_pct"]).sum() / top3["revenue_kes"].sum()

    first, last = monthly.iloc[0], monthly.iloc[-1]
    first_month = pd.to_datetime(first["month"]).strftime("%B")
    last_month = pd.to_datetime(last["month"]).strftime("%B")
    best_week = weekly.loc[weekly["revenue_kes"].idxmax(), "week_start"]

    report = f"""# Kisumu Fish Market: First Quarter of Digital Sales

**Prepared for:** County Government sponsor, Kisumu Fish Market Association
**Period:** 3 August to 31 October 2026 · {len(vendors)} vendors · {int(vendors['sales'].sum())} recorded sales · {kes(total)} total revenue

## Findings

**1. Three vendors earn {top3_share:.0f}% of the market's revenue.** {names}.

**2. Retail earns more per kg; wholesale earns more in total.** Retail buyers paid KES {retail['kes_per_kg']:,.0f}/kg against KES {wholesale['kes_per_kg']:,.0f}/kg for wholesale, a {premium:.0f}% premium; within each fish type the premium is {low:.0f}% to {high:.0f}%. Wholesale still brought in {wholesale_share:.0f}% of revenue, because the average wholesale sale was {wholesale['avg_kg_per_sale']:.0f} kg against {retail['avg_kg_per_sale']:.0f} kg.

**3. Revenue is trending {verdict}.** Average revenue per selling day went from {kes(first['revenue_per_day'])} in {first_month} to {kes(last['revenue_per_day'])} in {last_month}. The weekly trend line moves {change_pct:+.0f}% across the quarter, though single weeks swing widely; the best week began {best_week.day} {best_week:%B}.

![Weekly revenue](charts/weekly_revenue.png)

## Recommendation

Connect the {count_word(len(others))} smaller vendors to wholesale buyers such as schools and hotels. The top three earn {top3_wholesale:.0f}% of their revenue from wholesale; the other {count_word(len(others))} earn {others['wholesale_pct'].min():.0f}% to {others['wholesale_pct'].max():.0f}% and together hold only {others_share:.0f}% of the market. Bulk contracts would spread the growth beyond three stalls, while retail sales keep the higher price per kg.

*Note: the records show selling prices, not what vendors paid for fish, so "profitable per kg" here means revenue earned per kg.*
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    return report


def show(title, df):
    print(f"\n{title}")
    print("-" * len(title))
    print(df.to_string(index=False))


def main():
    try:
        conn = connect()
    except ReportError as err:
        print(f"Report not built: {err}")
        sys.exit(1)

    with conn:
        vendors = pd.read_sql_query(Q1_TOP_VENDORS, conn)
        buyers = pd.read_sql_query(Q2_BUYER_TYPE, conn)
        by_fish = pd.read_sql_query(Q2_BY_FISH, conn)
        weekly = pd.read_sql_query(Q3_WEEKLY, conn, parse_dates=["week_start"])
        monthly = pd.read_sql_query(Q3_MONTHLY, conn)
    conn.close()

    vendors["share_pct"] = (vendors["revenue_kes"]
                            / vendors["revenue_kes"].sum() * 100).round(1)
    buyers["revenue_share_pct"] = (buyers["revenue_kes"]
                                   / buyers["revenue_kes"].sum() * 100).round(1)
    by_fish["retail_premium_pct"] = ((by_fish["retail_kes_per_kg"]
                                      / by_fish["wholesale_kes_per_kg"] - 1)
                                     * 100).round(1)
    fitted, slope, change_pct, verdict = classify_trend(weekly)

    show("Q1. Revenue by vendor (top three answer the question)", vendors)
    show("Q2. Retail vs wholesale, revenue per kg", buyers)
    show("Q2 check. Revenue per kg inside each fish type", by_fish)
    show("Q3. Weekly revenue", weekly.assign(
        week_start=weekly["week_start"].dt.strftime("%Y-%m-%d"),
        trend_line=fitted.round()))
    show("Q3 check. Monthly revenue per day with sales", monthly)

    print(f"\nTrend line: {slope:+,.0f} KES per week, "
          f"{change_pct:+.1f}% of an average week across the quarter -> {verdict}")

    plot_weekly(weekly, fitted, verdict, change_pct)
    report = write_report(vendors, buyers, by_fish, monthly, weekly,
                          change_pct, verdict)
    print(f"\nChart saved:  {CHART_PATH.relative_to(BASE_DIR)}")
    print(f"Report saved: {REPORT_PATH.relative_to(BASE_DIR)}")
    print("\n" + report)


if __name__ == "__main__":
    main()
