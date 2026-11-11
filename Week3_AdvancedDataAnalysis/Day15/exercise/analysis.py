"""
Nairobi Produce Market: which vegetable is most volatile?
---------------------------------------------------------
Build plan
  Problem : a market analyst wants to know which of five vegetables has the
            most volatile price, and when that price peaks.
  Input   : data/vegetable_prices.csv (date, vegetable, price_kes_per_kg).
  Processing : compare the coefficient of variation, smooth each series with a
               7-day rolling average, and find the peak of the most volatile.
  Output  : a summary table on screen, charts/vegetable_prices.png, and a
            written finding for the market report.

Usage:
    python analysis.py
    python analysis.py path/to/vegetable_prices.csv

Requirements:
    pip install pandas numpy matplotlib
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DEFAULT_DATA = BASE_DIR / "data" / "vegetable_prices.csv"
CHART_DIR = BASE_DIR / "charts"
CHART_PATH = CHART_DIR / "vegetable_prices.png"

PRICE = "price_kes_per_kg"
WINDOW = 7


class DataError(Exception):
    """Raised when the input can't be used, with a message an analyst understands."""


def load_data(path):
    """Read the CSV, check the shape and pivot to one column per vegetable."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}. Run generate_sample_data.py first.")

    missing = {"date", "vegetable", PRICE} - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): "
                        f"{', '.join(sorted(missing))}. Expected: date, vegetable, "
                        f"{PRICE}.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[PRICE] = pd.to_numeric(df[PRICE], errors="coerce")
    if df["date"].isna().any():
        raise DataError("Some dates are not real dates. Use the format 2026-05-01.")
    if df[PRICE].isna().any():
        raise DataError("Some prices are missing or not numbers.")
    if (df[PRICE] <= 0).any():
        raise DataError("Some prices are zero or less. Check the source file.")

    df = df.drop_duplicates(subset=["date", "vegetable"], keep="last")
    prices = (df.pivot(index="date", columns="vegetable", values=PRICE)
              .sort_index())
    return prices


def summarise(prices):
    """Mean, spread, volatility and peak for each vegetable."""
    rows = []
    for vegetable in prices.columns:
        series = prices[vegetable].dropna()
        rolling = series.rolling(WINDOW, min_periods=WINDOW).mean()
        peak_date = rolling.idxmax()
        peak_price = rolling.max()

        rows.append({
            "vegetable": vegetable,
            "mean": series.mean(),
            "std": series.std(),
            # CV puts vegetables with different price levels on one scale.
            "cv_pct": series.std() / series.mean() * 100,
            "min": series.min(),
            "max": series.max(),
            "peak_date": peak_date,
            "peak_price": peak_price,
        })

    return pd.DataFrame(rows).set_index("vegetable").sort_values("cv_pct", ascending=False)


def plot_prices(prices, summary):
    """One panel per vegetable, with the 7-day average and its peak marked."""
    vegetables = list(prices.columns)
    fig, axes = plt.subplots(3, 2, figsize=(13, 10.5), sharex=True)
    axes = axes.flatten()

    for ax, vegetable in zip(axes, vegetables):
        series = prices[vegetable].dropna()
        rolling = series.rolling(WINDOW, min_periods=WINDOW).mean()
        row = summary.loc[vegetable]

        ax.plot(series.index, series.values, color="#9DC3E6", linewidth=0.9,
                label="Daily price")
        ax.plot(rolling.index, rolling.values, color="#C00000", linewidth=2,
                label=f"{WINDOW}-day average")
        ax.scatter([row["peak_date"]], [row["peak_price"]], color="#1F4E79",
                   s=45, zorder=4)
        # Keep the label inside the panel: left column labels to the right,
        # right column labels to the left.
        left_column = vegetables.index(vegetable) % 2 == 0
        ax.annotate(f"peak KES {row['peak_price']:.0f}\n{row['peak_date']:%d %b}",
                    xy=(row["peak_date"], row["peak_price"]),
                    xytext=(8, 12) if left_column else (-12, 12),
                    textcoords="offset points",
                    ha="left" if left_column else "right",
                    fontsize=8.5, color="#1F4E79")

        # Headroom so the peak label never touches the top edge.
        low, high = series.min(), series.max()
        ax.set_ylim(low - (high - low) * 0.08, high + (high - low) * 0.22)

        ax.set_title(f"{vegetable}  ·  volatility (CV) {row['cv_pct']:.1f}%",
                     fontsize=11, pad=6)
        ax.set_ylabel("KES per kg")
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)

    # The sixth slot is empty: five vegetables, not six.
    axes[-1].set_visible(False)
    axes[-1].axis("off")

    for ax in axes[:5]:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    for ax in axes[3:5]:
        ax.set_xlabel("2026")

    axes[0].legend(loc="upper left", frameon=False, fontsize=9)

    fig.suptitle("Nairobi Produce Market: Daily Prices, May to October 2026",
                 fontsize=15, y=0.985)
    fig.text(0.5, 0.955,
             "Bold line is the 7-day average. Higher CV means a less predictable price.",
             ha="center", fontsize=10.5, color="#444444")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def build_finding(summary):
    """The one-sentence conclusion for the market report."""
    most = summary.index[0]
    least = summary.index[-1]
    row = summary.loc[most]

    return (f"{most} were the most volatile vegetable, with a coefficient of variation of "
            f"{row['cv_pct']:.1f}% and a 7-day average peaking at KES "
            f"{row['peak_price']:.0f}/kg on {row['peak_date']:%d %B %Y}; "
            f"{least.lower()} were the steadiest at {summary.loc[least, 'cv_pct']:.1f}%.")


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    try:
        prices = load_data(data_path)
        summary = summarise(prices)
        plot_prices(prices, summary)
        finding = build_finding(summary)
    except DataError as error:
        sys.exit(f"Can't complete the analysis. {error}")

    print(f"Period: {prices.index.min():%d %b %Y} to {prices.index.max():%d %b %Y} "
          f"({len(prices)} days)")
    print("\nVolatility ranking (coefficient of variation)")
    print(f"  {'Vegetable':<10}{'Mean':>8}{'Std':>8}{'CV %':>8}{'Low':>8}{'High':>8}"
          f"    {'Peak (7-day avg)':>22}")
    for vegetable, row in summary.iterrows():
        print(f"  {vegetable:<10}{row['mean']:>8.1f}{row['std']:>8.1f}"
              f"{row['cv_pct']:>8.1f}{row['min']:>8.0f}{row['max']:>8.0f}"
              f"    {row['peak_date']:%d %b %Y}  KES {row['peak_price']:>4.0f}")

    print("\nMonthly average price (KES per kg)")
    monthly = prices.resample("MS").mean().round(1)
    print(monthly.to_string())

    print(f'\nFinding:\n  "{finding}"')
    print(f"\nChart saved: {CHART_PATH}")


if __name__ == "__main__":
    main()
