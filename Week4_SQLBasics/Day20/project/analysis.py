"""
Baraka Distributors: Q1 2024 database analysis
----------------------------------------------
Build plan
  Problem : the owner of Baraka Distributors wants a first-quarter review
            that answers three business questions:
              1. Which products drive revenue?
              2. Where is revenue concentrated, and which county is
                 underpenetrated?
              3. Is the business growing month to month, and is every county
                 keeping up?
  Input   : data/baraka_distributors.db, built by generate_baraka_data.py.
  Processing : SQL gets the data (totals, counts, monthly figures with LAG);
               pandas shapes the insight (shares, cumulative share, a
               county-by-month table, the Mombasa gap).
  Output  : the tables on screen, charts/baraka_analysis.png, and
            findings_report.md for the client.

Usage:
    python generate_baraka_data.py
    python analysis.py

Requirements:
    pip install pandas matplotlib
"""

import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "baraka_distributors.db"
CHART_PATH = BASE_DIR / "charts" / "baraka_analysis.png"
REPORT_PATH = BASE_DIR / "findings_report.md"

REQUIRED_COLUMNS = {"date", "product", "county", "quantity", "unit_price"}

# Mombasa is measured against the smallest of the other counties, not against
# Nairobi. Matching the weakest established market is a target a new sales
# contact can actually reach in a quarter.
FOCUS_COUNTY = "Mombasa"

Q1_PRODUCTS = """
    SELECT product,
           SUM(quantity * unit_price) AS total_revenue,
           SUM(quantity) AS total_units,
           COUNT(*) AS order_count
    FROM sales
    GROUP BY product
    ORDER BY total_revenue DESC
"""

Q2_COUNTIES = """
    SELECT county,
           SUM(quantity * unit_price) AS revenue,
           SUM(quantity) AS units,
           COUNT(*) AS orders,
           ROUND(1.0 * SUM(quantity * unit_price) / COUNT(*)) AS avg_order_value
    FROM sales
    GROUP BY county
    ORDER BY revenue DESC
"""

# LAG puts last month's revenue on this month's row, so the change is
# calculated in SQL without joining the table to itself.
Q3_MONTHLY = """
    WITH monthly AS (
        SELECT strftime('%Y-%m', date) AS month,
               SUM(quantity * unit_price) AS revenue,
               COUNT(*) AS orders
        FROM sales
        GROUP BY month
    )
    SELECT month,
           revenue,
           orders,
           ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                 / LAG(revenue) OVER (ORDER BY month), 1) AS change_pct
    FROM monthly
    ORDER BY month
"""

Q3_COUNTY_MONTHLY = """
    SELECT county,
           strftime('%Y-%m', date) AS month,
           SUM(quantity * unit_price) AS revenue,
           COUNT(*) AS orders
    FROM sales
    GROUP BY county, month
    ORDER BY county, month
"""


class ReportError(Exception):
    """Raised when the report can't be built, with a message a client understands."""


def connect():
    """Open the database read-only; an analysis must never change the records."""
    if not DB_PATH.exists():
        raise ReportError(
            f"Can't find the sales database at {DB_PATH}. "
            "Run generate_baraka_data.py first."
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sales)")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        conn.close()
        raise ReportError(
            "The sales table is missing these columns: "
            + ", ".join(sorted(missing))
            + ". Rebuild it with generate_baraka_data.py."
        )
    bad_dates = conn.execute(
        "SELECT COUNT(*) FROM sales WHERE date(date) IS NULL"
    ).fetchone()[0]
    if bad_dates:
        conn.close()
        raise ReportError(
            f"{bad_dates} order(s) have a date that is not a real date "
            "(expected YYYY-MM-DD). Correct them before running the analysis."
        )
    if conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        conn.close()
        raise ReportError("The sales table is empty, so there is nothing to analyse.")
    return conn


def kes(value):
    return f"KES {value:,.0f}"


def millions(value):
    return f"KES {value / 1_000_000:,.1f}M"


def month_name(month):
    return pd.to_datetime(month).strftime("%B")


def plot(products, counties, county_month):
    CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    to_millions = mticker.FuncFormatter(lambda v, _: f"{v / 1_000_000:,.0f}M")

    ordered = counties.sort_values("revenue")
    colours = ["#C00000" if c == FOCUS_COUNTY else "#1F4E79" for c in ordered["county"]]
    axes[0].barh(ordered["county"], ordered["revenue"], color=colours)
    for y, (rev, share) in enumerate(zip(ordered["revenue"], ordered["revenue_share_pct"])):
        axes[0].text(rev, y, f" {share:.1f}%", va="center", fontsize=9)
    axes[0].set_title("1. Revenue by county\n(Mombasa in red)", fontweight="bold")
    axes[0].set_xlabel("Revenue (KES)")
    axes[0].xaxis.set_major_locator(mticker.MultipleLocator(5_000_000))
    axes[0].xaxis.set_major_formatter(to_millions)
    axes[0].set_xlim(0, ordered["revenue"].max() * 1.18)

    axes[1].bar(products["product"], products["total_revenue"], color="#2E75B6")
    for x, share in enumerate(products["revenue_share_pct"]):
        axes[1].text(x, products["total_revenue"].iloc[x], f"{share:.0f}%",
                     ha="center", va="bottom", fontsize=9)
    axes[1].set_title("2. Revenue by product", fontweight="bold")
    axes[1].set_ylabel("Revenue (KES)")
    axes[1].yaxis.set_major_formatter(to_millions)
    axes[1].tick_params(axis="x", rotation=20)

    # Blues and greys for the other counties so red belongs to Mombasa alone.
    others = iter(["#1F4E79", "#2E75B6", "#7F7F7F", "#9DC3E6", "#404040"])
    labels = [pd.to_datetime(m).strftime("%b") for m in county_month.columns]
    for county in county_month.index:
        is_focus = county == FOCUS_COUNTY
        axes[2].plot(labels, county_month.loc[county], marker="o",
                     linewidth=3 if is_focus else 1.8,
                     color="#C00000" if is_focus else next(others), label=county)
    axes[2].set_title("3. Monthly revenue by county", fontweight="bold")
    axes[2].set_xlabel("Month (2024)")
    axes[2].set_ylabel("Revenue (KES)")
    axes[2].yaxis.set_major_formatter(to_millions)
    axes[2].set_ylim(bottom=0)
    axes[2].legend(fontsize=9, ncol=2)

    for ax in axes:
        ax.grid(alpha=0.3)
        ax.set_axisbelow(True)

    fig.suptitle("Baraka Distributors, Q1 2024: where the revenue comes from",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def write_report(products, counties, monthly, county_month, gap):
    total = products["total_revenue"].sum()
    top, second = products.iloc[0], products.iloc[1]
    top_two_share = top["revenue_share_pct"] + second["revenue_share_pct"]

    lead, runner = counties.iloc[0], counties.iloc[1]
    lead_two_share = lead["revenue_share_pct"] + runner["revenue_share_pct"]
    focus = counties.set_index("county").loc[FOCUS_COUNTY]
    network_avg_order = total / counties["orders"].sum()

    first, last = monthly.iloc[0], monthly.iloc[-1]
    quarter_growth = (last["revenue"] / first["revenue"] - 1) * 100
    county_change = (county_month.iloc[:, -1] / county_month.iloc[:, 0] - 1) * 100
    falling = county_change[county_change < 0].sort_values()
    focus_steps = [f"{kes(v)} in {month_name(m)}"
                   for m, v in county_month.loc[FOCUS_COUNTY].items()]
    focus_path = ", ".join(focus_steps[:-1]) + " and " + focus_steps[-1]
    if falling.empty:
        county_trend = "Every county ended the quarter above its January level."
    else:
        listed = " and ".join(f"{c} ({pct:+.0f}%)" for c, pct in falling.items())
        county_trend = (f"Not every county kept up: {listed} ended "
                        f"{month_name(last['month'])} below their "
                        f"{month_name(first['month'])} level.")

    report = f"""# Project Findings Report: Baraka Distributors Q1 2024

**Period:** 2 January to 30 March 2024 · {int(counties['orders'].sum())} orders · {len(counties)} counties · {len(products)} products
**Total revenue:** {kes(total)}

![Baraka Distributors Q1 2024](charts/baraka_analysis.png)

## 1. Top revenue driver

**{top['product']}** earned {kes(top['total_revenue'])}, {top['revenue_share_pct']:.0f}% of total revenue. Second is **{second['product']}** at {kes(second['total_revenue'])}. Together these two products generate **{top_two_share:.0f}%** of all revenue. {products.iloc[-1]['product']} is the smallest line at {products.iloc[-1]['revenue_share_pct']:.0f}%.

## 2. Geographic concentration

**{lead['county']}** ({lead['revenue_share_pct']:.1f}%) and **{runner['county']}** ({runner['revenue_share_pct']:.1f}%) account for **{lead_two_share:.0f}%** of sales. **{FOCUS_COUNTY}** is significantly underpenetrated at **{focus['revenue_share_pct']:.1f}%**.

The problem in {FOCUS_COUNTY} is how often shops order, not how much they order. {FOCUS_COUNTY} placed **{int(focus['orders'])} orders** in the quarter, against {int(lead['orders'])} in {lead['county']}, yet its average order was {kes(focus['avg_order_value'])}, close to the network average of {kes(network_avg_order)}. The shops that buy are buying properly; there are too few of them.

## 3. Month-to-month trend

Revenue grew from {millions(first['revenue'])} in {month_name(first['month'])} to {millions(last['revenue'])} in {month_name(last['month'])}, up **{quarter_growth:.0f}%** across the quarter. {month_name(monthly.iloc[1]['month'])} changed by {monthly.iloc[1]['change_pct']:+.1f}% and {month_name(last['month'])} by {last['change_pct']:+.1f}%.

{county_trend} {FOCUS_COUNTY} took {focus_path}. While the network grew, {FOCUS_COUNTY} shrank, so the gap is widening rather than closing on its own.

## Recommendation

**Increase {FOCUS_COUNTY} stock allocation and assign a dedicated sales contact for that county.** The target is realistic: if {FOCUS_COUNTY} matched {gap['benchmark']}, the smallest established county ({kes(gap['benchmark_revenue'])} this quarter), it would add about **{kes(gap['gap'])} per quarter**, roughly {gap['extra_orders']:.0f} more orders at {FOCUS_COUNTY}'s current order size. The contact's job is to win more shops, not bigger orders, since order size is already in line with the network.

*Data: Baraka Distributors sales database, `sales` table. Figures produced by `analysis.py`; synthetic practice data.*
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
        print(f"Analysis not built: {err}")
        sys.exit(1)

    with conn:
        products = pd.read_sql_query(Q1_PRODUCTS, conn)
        counties = pd.read_sql_query(Q2_COUNTIES, conn)
        monthly = pd.read_sql_query(Q3_MONTHLY, conn)
        county_month_long = pd.read_sql_query(Q3_COUNTY_MONTHLY, conn)
    conn.close()

    if FOCUS_COUNTY not in set(counties["county"]):
        print(f"Analysis not built: there are no {FOCUS_COUNTY} orders in the database.")
        sys.exit(1)

    products["revenue_share_pct"] = (products["total_revenue"]
                                     / products["total_revenue"].sum() * 100).round(1)
    products["cumulative_share_pct"] = products["revenue_share_pct"].cumsum().round(1)

    counties["revenue_share_pct"] = (counties["revenue"]
                                     / counties["revenue"].sum() * 100).round(1)
    counties = counties.sort_values("revenue", ascending=False).reset_index(drop=True)

    # A county with no orders in a month is a real zero, not a missing value.
    county_month = (county_month_long
                    .pivot(index="county", columns="month", values="revenue")
                    .fillna(0)
                    .reindex(counties["county"]))

    others = counties[counties["county"] != FOCUS_COUNTY]
    benchmark = others.loc[others["revenue"].idxmin()]
    focus = counties.set_index("county").loc[FOCUS_COUNTY]
    gap_kes = benchmark["revenue"] - focus["revenue"]
    gap = {
        "benchmark": benchmark["county"],
        "benchmark_revenue": benchmark["revenue"],
        "gap": gap_kes,
        "extra_orders": gap_kes / focus["avg_order_value"],
    }

    show("Q1. Revenue by product", products)
    show("Q2. Revenue by county", counties)
    show("Q3. Revenue by month", monthly)
    print("\nQ3 check. Revenue by county and month (KES)")
    print("-------------------------------------------")
    print(county_month.map(lambda v: f"{v:,.0f}").to_string())
    print(f"\n{FOCUS_COUNTY} gap to {gap['benchmark']}: {kes(gap['gap'])} "
          f"(about {gap['extra_orders']:.0f} orders)")

    plot(products, counties, county_month)
    report = write_report(products, counties, monthly, county_month, gap)
    print(f"\nChart saved:  {CHART_PATH.relative_to(BASE_DIR)}")
    print(f"Report saved: {REPORT_PATH.relative_to(BASE_DIR)}")
    print("\n" + report)


if __name__ == "__main__":
    main()
