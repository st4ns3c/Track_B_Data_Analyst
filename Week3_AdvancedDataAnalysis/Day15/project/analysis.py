"""
Distributor Performance: August vs September 2026
-------------------------------------------------
Build plan
  Problem : a distributor sells in Nairobi and Mombasa. The manager wants a
            clear picture of the two months: total revenue, which region
            carries the business, which customers matter, and what changed.
  Input   : data/sales_august.csv, data/sales_september.csv. The two exports
            use different column names and a few different name spellings.
  Processing : standardise the columns, clean the customer names, stack the
               months, calculate revenue, then compare regions, months, tiers
               and customers.
  Output  : four charts in charts/project_analysis.png, a four-sentence
            findings summary on screen, and the numbers used in the README.

Usage:
    python analysis.py

Requirements:
    pip install pandas numpy matplotlib
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHART_DIR = BASE_DIR / "charts"
CHART_PATH = CHART_DIR / "project_analysis.png"

MONTHS = ["August", "September"]

# Tier thresholds are set for this distributor's size, not copied blindly from
# the lesson. Two-month revenue above KES 250,000 is a major account.
TIER_HIGH = 250000
TIER_MEDIUM = 60000


class DataError(Exception):
    """Raised when a file can't be used, with a message a manager understands."""


def clean_name(name):
    """'kamau stores', 'KAMAU STORES ' and 'Kamau  Stores' are one customer."""
    return " ".join(str(name).split()).title()


def load_month(path, columns, month):
    """Read one monthly export, rename its columns and validate the rows."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}. Run generate_sample_data.py first.")

    missing = set(columns) - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): "
                        f"{', '.join(sorted(missing))}. Expected: {', '.join(columns)}.")

    df = df.rename(columns=columns).copy()
    df["month"] = month
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        raise DataError(f"{bad_dates} row(s) in {Path(path).name} have a date that isn't a "
                        f"real date. Use the format 2026-08-15.")

    for column in ("quantity", "price"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_values = int(df[["quantity", "price"]].isna().any(axis=1).sum())
    if missing_values:
        raise DataError(f"{missing_values} row(s) in {Path(path).name} have a missing quantity "
                        f"or price.")

    if (df["quantity"] <= 0).any() or (df["price"] <= 0).any():
        raise DataError(f"{Path(path).name} has a quantity or price of zero or less.")

    df["customer"] = df["customer"].map(clean_name)
    duplicate_rows = int(df.duplicated().sum())
    df = df.drop_duplicates()

    print(f"  {Path(path).name:<24} {len(df):>3} rows, {duplicate_rows} duplicate(s) removed")
    return df


def load_all():
    """Load and stack both months into one tidy DataFrame."""
    august = load_month(
        DATA_DIR / "sales_august.csv",
        {"client_name": "customer", "county": "region", "qty": "quantity",
         "unit_price": "price"},
        "August",
    )
    september = load_month(
        DATA_DIR / "sales_september.csv",
        {"customer_name": "customer", "region": "region", "quantity": "quantity",
         "price": "price"},
        "September",
    )

    combined = pd.concat([august, september], ignore_index=True)
    combined["revenue"] = combined["quantity"] * combined["price"]
    return combined


def revenue_by(combined):
    """The three views the charts and findings need."""
    by_region = combined.groupby("region")["revenue"].sum().sort_values(ascending=False)
    by_month = combined.groupby("month")["revenue"].sum().reindex(MONTHS)
    by_region_month = (combined.pivot_table(index="region", columns="month",
                                            values="revenue", aggfunc="sum")
                       .reindex(columns=MONTHS))
    orders_by_region = combined.groupby("region").size()
    return by_region, by_month, by_region_month, orders_by_region


def customer_table(combined):
    """Total revenue and tier per customer, plus the change between months."""
    totals = combined.groupby("customer")["revenue"].sum().reset_index()
    totals["tier"] = np.where(totals["revenue"] >= TIER_HIGH, "High",
                              np.where(totals["revenue"] >= TIER_MEDIUM, "Medium", "Low"))

    monthly = (combined.pivot_table(index="customer", columns="month",
                                    values="revenue", aggfunc="sum")
               .reindex(columns=MONTHS).fillna(0))
    monthly["change"] = monthly["September"] - monthly["August"]
    monthly["pct_change"] = np.where(
        monthly["August"] > 0,
        (monthly["September"] - monthly["August"]) / monthly["August"] * 100,
        np.nan,
    )
    return totals, monthly.sort_values("change", ascending=False)


def findings(combined, by_region, by_month, by_region_month, orders_by_region, totals, monthly):
    """Four sentences a non-technical manager can repeat in a meeting."""
    august, september = by_month["August"], by_month["September"]
    change = (september / august - 1) * 100

    total_revenue = by_region.sum()
    nairobi_share = by_region["Nairobi"] / total_revenue * 100
    order_share = orders_by_region["Nairobi"] / orders_by_region.sum() * 100

    nairobi_growth = (by_region_month.loc["Nairobi", "September"] /
                      by_region_month.loc["Nairobi", "August"] - 1) * 100
    mombasa_growth = (by_region_month.loc["Mombasa", "September"] /
                      by_region_month.loc["Mombasa", "August"] - 1) * 100

    top_names = totals.sort_values("revenue", ascending=False).head(3)["customer"].tolist()
    top_august = monthly.loc[top_names, "August"].sum()
    top_september = monthly.loc[top_names, "September"].sum()
    top_growth = (top_september / top_august - 1) * 100
    top_share = top_september / september * 100

    others = monthly.drop(index=top_names)
    others_august = others["August"].sum()
    others_september = others["September"].sum()
    others_change = (others_september / others_august - 1) * 100

    dormant = monthly[(monthly["August"] > 0) & (monthly["September"] == 0)]
    dormant_revenue = dormant["August"].sum()

    summary = [
        f"Revenue fell {abs(change):.1f}% from August (KES {august:,.0f}) to September "
        f"(KES {september:,.0f}), a drop of KES {august - september:,.0f}.",

        f"Nairobi contributed {nairobi_share:.0f}% of revenue from {order_share:.0f}% of "
        f"order lines, and its revenue rose {nairobi_growth:.1f}% while Mombasa fell "
        f"{abs(mombasa_growth):.1f}%.",

        f"The three biggest customers ({', '.join(top_names)}) now account for "
        f"{top_share:.0f}% of revenue and grew {top_growth:.0f}% in September, so the "
        f"overall decline came from smaller accounts, which fell {abs(others_change):.1f}%.",

        f"{len(dormant)} customers who ordered in August placed no order in September, "
        f"representing KES {dormant_revenue:,.0f} of dormant revenue worth chasing before "
        f"the end of the quarter.",
    ]
    return summary, dict(
        top_growth=top_growth, top_share=top_share, dormant=dormant,
        dormant_revenue=dormant_revenue, others_change=others_change,
    )


def kes_short(value):
    """Axis and bar labels in a size a manager can read at a glance."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value / 1000:,.0f}k"


def plot_dashboard(by_region, by_month, by_region_month, totals):
    """Four charts, each answering one question."""
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))

    # 1. Where does revenue come from?
    bars = axes[0, 0].bar(by_region.index, by_region.values, color="#1F4E79", width=0.55)
    axes[0, 0].bar_label(bars, labels=[f"KES {kes_short(v)}" for v in by_region.values],
                         padding=3, fontsize=9)
    axes[0, 0].set_title("Where does revenue come from?", fontsize=11.5, pad=8)
    axes[0, 0].set_ylabel("Revenue (KES)")

    # 2. How did the two months compare?
    bars = axes[0, 1].bar(by_month.index, by_month.values, color="#4472C4", width=0.55)
    axes[0, 1].bar_label(bars, labels=[f"KES {kes_short(v)}" for v in by_month.values],
                         padding=3, fontsize=9)
    axes[0, 1].set_title("How did the two months compare?", fontsize=11.5, pad=8)
    axes[0, 1].set_ylabel("Revenue (KES)")

    # 3. How concentrated is the customer base? Slices are revenue, not customer
    # count: three accounts hold most of the money, which is the point.
    tiers = (totals.groupby("tier")
             .agg(customers=("customer", "count"), revenue=("revenue", "sum"))
             .reindex(["High", "Medium", "Low"]))
    axes[1, 0].pie(tiers["revenue"],
                   labels=[f"{tier}\n{int(row['customers'])} customers"
                           for tier, row in tiers.iterrows()],
                   colors=["#1F4E79", "#2E75B6", "#9DC3E6"], autopct="%1.0f%%",
                   startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                   textprops={"fontsize": 9.5})
    axes[1, 0].set_title("How concentrated is the customer base?", fontsize=11.5, pad=8)
    axes[1, 0].text(0.5, -0.12, "Slices show share of revenue, not share of customers.",
                    transform=axes[1, 0].transAxes, ha="center", fontsize=8.5,
                    color="#555555")

    # 4. Which region drove the change?
    x = np.arange(len(by_region_month.index))
    width = 0.35
    axes[1, 1].bar(x - width / 2, by_region_month["August"], width,
                   label="August", color="#9DC3E6")
    axes[1, 1].bar(x + width / 2, by_region_month["September"], width,
                   label="September", color="#1F4E79")
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(by_region_month.index)
    axes[1, 1].set_title("Which region drove the change?", fontsize=11.5, pad=8)
    axes[1, 1].set_ylabel("Revenue (KES)")
    axes[1, 1].legend(frameon=False, fontsize=9)

    for ax in (axes[0, 0], axes[0, 1], axes[1, 1]):
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: kes_short(value)))
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    fig.suptitle("Distributor Performance: August vs September 2026", fontsize=15, y=0.985)
    fig.text(0.5, 0.945,
             "Nairobi is the engine; the smaller Mombasa accounts are where the decline sits.",
             ha="center", fontsize=10.5, color="#444444")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def main():
    try:
        print("Loading")
        combined = load_all()
        by_region, by_month, by_region_month, orders_by_region = revenue_by(combined)
        totals, monthly = customer_table(combined)
        summary, extra = findings(combined, by_region, by_month, by_region_month,
                                  orders_by_region, totals, monthly)
        plot_dashboard(by_region, by_month, by_region_month, totals)
    except DataError as error:
        sys.exit(f"Can't complete the analysis. {error}")

    total = combined["revenue"].sum()
    print(f"\nCombined: {len(combined):,} order lines | KES {total:,.0f} revenue")
    print("\nRevenue by region")
    for region, value in by_region.items():
        print(f"  {region:<8} KES {value:>11,.0f}   {value / total * 100:5.1f}%")
    print("\nRevenue by month")
    for month, value in by_month.items():
        print(f"  {month:<10} KES {value:>11,.0f}")
    print("\nCustomer tiers")
    for tier, count in totals["tier"].value_counts().reindex(["High", "Medium", "Low"]).items():
        print(f"  {tier:<7} {int(count)}")
    print("\nTop 3 customers")
    for _, row in totals.sort_values("revenue", ascending=False).head(3).iterrows():
        print(f"  {row['customer']:<20} KES {row['revenue']:>10,.0f}   {row['tier']}")
    print("\nDormant accounts")
    for customer in extra["dormant"].index:
        print(f"  {customer:<20} KES {extra['dormant'].loc[customer, 'August']:>10,.0f} in August")

    print("\nFindings")
    for number, sentence in enumerate(summary, start=1):
        print(f"  {number}. {sentence}")

    print(f"\nChart saved: {CHART_PATH}")


if __name__ == "__main__":
    main()
