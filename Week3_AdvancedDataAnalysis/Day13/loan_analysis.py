"""
Mombasa Microfinance: Loan Book Statistical Summary
---------------------------------------------------
Build plan
  Problem : a Mombasa microfinance institution wants to describe its loan book
            to the board: the typical loan, unusual loans, and whether loan
            size is linked to how quickly the first repayment arrives.
  Input   : data/loans.csv (loan_id, amount_kes, days_to_first_repayment, county).
  Processing : descriptive statistics, the IQR outlier rule, Pearson
               correlation, and a histogram of loan amounts.
  Output  : a printed summary for the analyst, loan_amounts.png for the board,
            and a plain-language finding.

Usage:
    python loan_analysis.py
    python loan_analysis.py path/to/loans.csv

Requirements:
    pip install pandas numpy matplotlib scipy
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).parent
DEFAULT_DATA = BASE_DIR / "data" / "loans.csv"
CHART_PATH = BASE_DIR / "loan_amounts.png"

AMOUNT = "amount_kes"
DAYS = "days_to_first_repayment"


class DataError(Exception):
    """Raised when the input can't be used, with a message a manager understands."""


def load_data(path):
    """Read the CSV and make sure the numbers are usable before analysing them."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}. Run generate_sample_data.py first.")

    required = ["loan_id", AMOUNT, DAYS, "county"]
    missing = set(required) - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): "
                        f"{', '.join(sorted(missing))}. Expected: {', '.join(required)}.")

    for column in (AMOUNT, DAYS):
        df[column] = pd.to_numeric(df[column], errors="coerce")
        bad = int(df[column].isna().sum())
        if bad:
            raise DataError(f"{bad} row(s) have a value in {column} that isn't a number.")

    if (df[AMOUNT] <= 0).any():
        raise DataError("Some loans have an amount of zero or less. Check the source file.")
    if (df[DAYS] < 0).any():
        raise DataError("Some loans have a negative repayment time. Check the source file.")
    if df["loan_id"].duplicated().any():
        duplicated = df.loc[df["loan_id"].duplicated(), "loan_id"].iloc[0]
        raise DataError(f"Loan ID {duplicated} appears more than once.")

    return df


def print_descriptive_stats(df):
    """The full summary: mean, median, spread, quartiles and range."""
    table = pd.DataFrame({
        "Loan amount (KES)": df[AMOUNT].describe(),
        "Days to first repayment": df[DAYS].describe(),
    })
    table.index = ["Count", "Mean", "Std deviation", "Minimum",
                   "25th percentile (Q1)", "Median (Q2)", "75th percentile (Q3)", "Maximum"]

    print("\nSummary statistics")
    print(f"  {'Measure':<24}{'Loan amount (KES)':>20}{'Days to repayment':>22}")
    for measure, row in table.iterrows():
        if measure == "Count":
            amount = f"{row['Loan amount (KES)']:,.0f}"
            days = f"{row['Days to first repayment']:,.0f}"
        else:
            amount = f"{row['Loan amount (KES)']:,.1f}"
            days = f"{row['Days to first repayment']:,.1f}"
        print(f"  {measure:<24}{amount:>20}{days:>22}")

    mean_amount = df[AMOUNT].mean()
    median_amount = df[AMOUNT].median()
    gap = (mean_amount / median_amount - 1) * 100
    print(f"\n  The mean loan (KES {mean_amount:,.0f}) is {gap:.0f}% higher than the median "
          f"(KES {median_amount:,.0f}).")
    print("  That gap is the signature of a skewed loan book: a few very large loans pull "
          "the average up.")


def iqr_outliers(series):
    """Return the IQR fences and the rows outside them."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    return q1, q3, iqr, lower, upper, mask


def print_outliers(df):
    """List the actual loan IDs outside the IQR fences, not just a count."""
    print("\nOutlier check: loan amount (IQR method)")
    q1, q3, iqr, lower, upper, mask = iqr_outliers(df[AMOUNT])
    print(f"  Q1 = KES {q1:,.0f}   Q3 = KES {q3:,.0f}   IQR = KES {iqr:,.0f}")
    print(f"  Anything below KES {lower:,.0f} or above KES {upper:,.0f} is unusual.")

    unusual = df[mask].sort_values(AMOUNT, ascending=False)
    if unusual.empty:
        print("  No loan amounts fall outside the fences.")
    else:
        print(f"  {len(unusual)} loan(s) above the fence:")
        for _, row in unusual.iterrows():
            print(f"    {row['loan_id']}   KES {row[AMOUNT]:>9,}   {row[DAYS]:>3} days   {row['county']}")
    if lower < 0:
        print("  No unusually small loans: the lower fence is below zero, and a loan "
              "cannot be negative.")

    print("\nOutlier check: days to first repayment (IQR method)")
    _, _, _, day_lower, day_upper, day_mask = iqr_outliers(df[DAYS])
    unusual_days = df[day_mask].sort_values(DAYS, ascending=False)
    print(f"  Anything above {day_upper:.0f} days is unusual.")
    if unusual_days.empty:
        print("  No repayment times fall outside the fence.")
    else:
        for _, row in unusual_days.iterrows():
            print(f"    {row['loan_id']}   {row[DAYS]:>3} days   KES {row[AMOUNT]:>9,}   {row['county']}")

    return unusual


def describe_correlation(df):
    """Pearson correlation, its p-value, and what it does and does not prove."""
    result = stats.pearsonr(df[AMOUNT], df[DAYS])
    r, p = result.statistic, result.pvalue
    strength = ("very weak" if abs(r) < 0.2 else
                "weak" if abs(r) < 0.4 else
                "moderate" if abs(r) < 0.6 else
                "strong" if abs(r) < 0.8 else "very strong")
    direction = "positive" if r > 0 else "negative"

    print("\nCorrelation: loan amount vs days to first repayment")
    print(f"  Pearson r = {r:.3f}   ({strength} {direction} relationship)")
    p_text = "< 0.0001" if p < 0.0001 else f"= {p:.4f}"
    print(f"  p-value   {p_text}   " +
          ("statistically significant at 5%." if p < 0.05
           else "not statistically significant at 5%."))
    print(f"  r-squared = {r ** 2:.3f}: loan size explains about {r ** 2 * 100:.0f}% of the "
          f"variation in repayment time.")

    if r >= 0.3:
        sentence = ("Larger loans tend to take somewhat longer to reach a first repayment, "
                    "but loan size is only part of the story.")
    elif r > 0:
        sentence = ("There is only a slight tendency for larger loans to take longer to reach "
                    "a first repayment, so loan size is not a useful guide on its own.")
    else:
        sentence = ("Larger loans do not take longer to reach a first repayment in this data; "
                    "if anything the link runs the other way.")

    print(f'\n  In plain words: "{sentence}"')
    print("  Remember: a correlation is not a cause. The data cannot say why the two move "
          "together.")
    return r, p, sentence


def kes_tick(value, _):
    """Axis labels in thousands, with one decimal only for the small ticks."""
    if value >= 1_000_000:
        return "1M"
    if value < 10_000:
        return f"{value / 1000:g}k"
    return f"{value / 1000:,.0f}k"


def plot_histogram(df):
    """A log-scale histogram, with the mean, median and outlier fence marked."""
    fig, ax = plt.subplots(figsize=(11, 6))

    bins = np.logspace(np.log10(2500), np.log10(950000), 26)
    ax.hist(df[AMOUNT], bins=bins, color="#9DC3E6", edgecolor="#2E75B6",
            linewidth=0.7, label="Loans per band")

    median = df[AMOUNT].median()
    mean = df[AMOUNT].mean()
    _, _, _, _, upper_fence, _ = iqr_outliers(df[AMOUNT])

    ax.axvline(median, color="#1E7145", linewidth=2,
               label=f"Median: KES {median:,.0f}")
    ax.axvline(mean, color="#C00000", linewidth=2, linestyle="--",
               label=f"Mean: KES {mean:,.0f}")
    ax.axvline(upper_fence, color="#BF8F00", linewidth=1.5, linestyle=":",
               label=f"Outlier fence: KES {upper_fence:,.0f}")

    q1, q3 = df[AMOUNT].quantile(0.25), df[AMOUNT].quantile(0.75)
    fig.suptitle("Mombasa Microfinance: Loan Amounts (150 loans)", fontsize=15, y=0.98)
    fig.text(0.5, 0.92,
             f"Half of all loans sit between KES {q1:,.0f} and KES {q3:,.0f}; "
             f"a few large loans pull the mean up.",
             ha="center", fontsize=10.5, color="#444444")

    ax.set_xscale("log")
    ax.set_xlim(2200, 1_200_000)
    ticks = [2500, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000]
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(FuncFormatter(kes_tick))
    ax.minorticks_off()

    ax.set_xlabel("Loan amount (KES, logarithmic scale)")
    ax.set_ylabel("Number of loans")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    ax.annotate("4 loans above KES 480k", xy=(950000, 1.0), xycoords="data",
                xytext=(0.60, 0.55), textcoords="axes fraction",
                ha="center", fontsize=9.5, color="#1F4E79",
                arrowprops=dict(arrowstyle="->", color="#1F4E79", lw=0.9))

    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def print_board_summary(df, outliers, sentence):
    """Step 5 of the lesson: statistics are only useful if they lead to a decision."""
    median = df[AMOUNT].median()
    mean = df[AMOUNT].mean()
    q1, q3 = df[AMOUNT].quantile(0.25), df[AMOUNT].quantile(0.75)
    largest = outliers.iloc[0] if not outliers.empty else None

    print("\nBoard summary")
    print(f"  Finding        : The median loan is KES {median:,.0f}; half of all loans are "
          f"between KES {q1:,.0f} and KES {q3:,.0f}.")
    if largest is not None:
        print(f"                   {len(outliers)} loans sit above the outlier fence; the "
              f"largest is {largest['loan_id']} at KES {largest[AMOUNT]:,}.")
    print(f"  What it means  : The mean (KES {mean:,.0f}) overstates the typical loan because "
          f"of those large accounts. Quote the median when describing the book.")
    print(f"  Recommendation : Review the large loans as a group for approval and exposure, "
          f"and use the median in board reporting. On repayment speed: {sentence.lower()}")


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    try:
        df = load_data(data_path)
        print(f"Loan book: {len(df)} records from {data_path.name}")
        print_descriptive_stats(df)
        outliers = print_outliers(df)
        r, _, sentence = describe_correlation(df)
        plot_histogram(df)
        print_board_summary(df, outliers, sentence)
    except DataError as error:
        sys.exit(f"Can't analyse the loan book. {error}")

    print(f"\nChart saved: {CHART_PATH.name}")


if __name__ == "__main__":
    main()
