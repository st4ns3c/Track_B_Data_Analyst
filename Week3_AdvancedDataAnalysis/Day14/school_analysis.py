"""
Kisumu Schools: Attendance vs Classrooms
----------------------------------------
Build plan
  Problem : a Kisumu County education officer wants to know whether schools
            with more classrooms have better attendance. The two files use
            different column names and school-name formats, and contain
            missing values and a duplicate row.
  Input   : data/attendance.csv      (school, average_attendance_pct, county)
            data/infrastructure.csv  (school_name, num_classrooms, water_access)
  Processing : standardise the names, remove duplicates, merge on the cleaned
               school name, then correlate classrooms with attendance.
  Output  : a data-quality and merge report on screen, and
            attendance_vs_classrooms.png for the officer.

Usage:
    python school_analysis.py
    python school_analysis.py path/to/attendance.csv path/to/infrastructure.csv

Requirements:
    pip install pandas numpy matplotlib scipy
"""

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # saves the chart without needing a screen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).parent
DEFAULT_ATTENDANCE = BASE_DIR / "data" / "attendance.csv"
DEFAULT_INFRASTRUCTURE = BASE_DIR / "data" / "infrastructure.csv"
CHART_PATH = BASE_DIR / "attendance_vs_classrooms.png"

ATTENDANCE = "average_attendance_pct"
CLASSROOMS = "num_classrooms"
WATER = "water_access"


class DataError(Exception):
    """Raised when a file can't be used, with a message a manager understands."""


def load_file(path, required):
    """Read a CSV and check the columns we need are there."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Can't find {path}. Run generate_sample_data.py first.")
    missing = set(required) - set(df.columns)
    if missing:
        raise DataError(f"{Path(path).name} is missing the column(s): "
                        f"{', '.join(sorted(missing))}. Expected: {', '.join(required)}.")
    return df


def clean_school_name(name):
    """Turn the many ways a school is typed into one key.

    'KISUMU BOYS HIGH SCHOOL', 'Kisumu Boys High School' and
    'Kisumu Boys High' all become 'kisumu boys high'. Abbreviations are
    expanded and the final word 'school' is dropped, because it adds no
    information and is the most common thing to be left off.
    """
    text = str(name).lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[.,'’]", "", text)
    text = re.sub(r"\s+", " ", text)

    replacements = {
        "pri": "primary", "pry": "primary", "prim": "primary",
        "sch": "school", "sec": "secondary",
    }
    words = [replacements.get(word, word) for word in text.split()]
    if words and words[-1] == "school":
        words.pop()
    return " ".join(words)


def clean_attendance(df):
    """Return the attendance rows with a clean key, and what was fixed."""
    df = df.copy()
    df["school"] = df["school"].astype(str)
    df[ATTENDANCE] = pd.to_numeric(df[ATTENDANCE], errors="coerce")
    df["school_key"] = df["school"].map(clean_school_name)

    missing_attendance = int(df[ATTENDANCE].isna().sum())
    duplicate_rows = int(df.duplicated().sum())
    df = df.drop_duplicates()

    duplicate_keys = df[df.duplicated("school_key", keep=False)]
    if not duplicate_keys.empty:
        names = ", ".join(sorted(duplicate_keys["school"].unique()))
        raise DataError(f"These schools appear more than once after cleaning: {names}. "
                        f"Fix the source file before merging.")

    print(f"  attendance.csv     : {len(df)} rows, {duplicate_rows} duplicate row(s) removed, "
          f"{missing_attendance} missing attendance value(s)")
    return df


def clean_infrastructure(df):
    """Return the infrastructure rows with a clean key, and what was fixed."""
    df = df.copy()
    df["school_name"] = df["school_name"].astype(str)
    df[CLASSROOMS] = pd.to_numeric(df[CLASSROOMS], errors="coerce")
    df["school_key"] = df["school_name"].map(clean_school_name)

    missing_classrooms = int(df[CLASSROOMS].isna().sum())
    missing_water = int(df[WATER].isna().sum())
    duplicate_rows = int(df.duplicated().sum())
    df = df.drop_duplicates()

    duplicate_keys = df[df.duplicated("school_key", keep=False)]
    if not duplicate_keys.empty:
        names = ", ".join(sorted(duplicate_keys["school_name"].unique()))
        raise DataError(f"These schools appear more than once after cleaning: {names}. "
                        f"Fix the source file before merging.")

    print(f"  infrastructure.csv : {len(df)} rows, {duplicate_rows} duplicate row(s) removed, "
          f"{missing_classrooms} missing classroom count(s), {missing_water} missing water record(s)")
    return df


def merge_files(attendance, infrastructure):
    """Inner-merge on the clean key and explain every school that was lost."""
    merged = attendance.merge(
        infrastructure[["school_key", "school_name", CLASSROOMS, WATER]],
        on="school_key", how="inner",
    )

    attendance_keys = set(attendance["school_key"])
    infrastructure_keys = set(infrastructure["school_key"])
    attendance_only = attendance_keys - infrastructure_keys
    infrastructure_only = infrastructure_keys - attendance_keys

    lookup = dict(zip(attendance["school_key"], attendance["school"]))
    lookup.update(zip(infrastructure["school_key"], infrastructure["school_name"]))

    print(f"\nMerge on school name")
    print(f"  Matched: {len(merged)} schools")
    if attendance_only:
        print("  In attendance only (no infrastructure row): "
              + ", ".join(sorted(lookup[key].strip() for key in attendance_only)))
    if infrastructure_only:
        print("  In infrastructure only (no attendance row): "
              + ", ".join(sorted(lookup[key] for key in infrastructure_only)))

    return merged


def analyse(merged):
    """Correlate classrooms with attendance and describe the result."""
    analysis = merged.dropna(subset=[ATTENDANCE, CLASSROOMS]).copy()
    analysis[WATER] = analysis[WATER].fillna("Not reported")

    if len(analysis) < 3:
        raise DataError("Fewer than three schools have both attendance and classrooms, "
                        "so a correlation would be meaningless.")

    x = analysis[CLASSROOMS].to_numpy()
    y = analysis[ATTENDANCE].to_numpy()
    result = stats.pearsonr(x, y)
    r, p = result.statistic, result.pvalue
    slope, intercept = np.polyfit(x, y, 1)

    strength = ("very weak" if abs(r) < 0.2 else
                "weak" if abs(r) < 0.4 else
                "moderate" if abs(r) < 0.6 else
                "strong" if abs(r) < 0.8 else "very strong")
    direction = "positive" if r > 0 else "negative"

    print(f"\nSchools used in the correlation: {len(analysis)} "
          f"(dropped {len(merged) - len(analysis)} for missing values)")
    print(f"  Attendance: {y.min():.1f}% to {y.max():.1f}%, mean {y.mean():.1f}%")
    print(f"  Classrooms: {x.min():.0f} to {x.max():.0f}, mean {x.mean():.1f}")
    print(f"\nCorrelation: classrooms vs attendance")
    print(f"  Pearson r = {r:.3f}   ({strength} {direction} relationship)")
    p_text = "< 0.0001" if p < 0.0001 else f"= {p:.4f}"
    print(f"  p-value   {p_text}   " +
          ("statistically significant at 5%." if p < 0.05
           else "not statistically significant at 5%."))
    print(f"  r-squared = {r ** 2:.3f}: classrooms explain about {r ** 2 * 100:.0f}% of the "
          f"variation in attendance.")
    print(f"  Slope     = {slope:+.2f} percentage points of attendance per extra classroom.")

    water = (analysis.groupby(WATER)[ATTENDANCE]
             .agg(count="count", mean="mean")
             .round(1)
             .sort_values("mean", ascending=False))
    print("\nAttendance by water access")
    for label, row in water.iterrows():
        print(f"  {label:<14} {int(row['count'])} school(s), mean attendance {row['mean']:.1f}%")

    if r >= 0.3 and p < 0.05:
        sentence = (f"Schools with more classrooms tend to have better attendance "
                    f"(r = {r:.2f}, n = {len(analysis)}): each extra classroom is associated "
                    f"with about {slope:.1f} percentage points more attendance, though this is "
                    f"an association and not proof that classrooms cause it.")
    elif p >= 0.05:
        sentence = (f"There is no clear link between the number of classrooms and attendance "
                    f"in these {len(analysis)} schools (r = {r:.2f}, p = {p:.3f}), so classroom "
                    f"count alone does not explain attendance.")
    else:
        sentence = (f"Schools with more classrooms tend to have slightly lower attendance "
                    f"(r = {r:.2f}, n = {len(analysis)}), which is the opposite of what was "
                    f"expected and worth checking against class sizes.")

    print(f'\nFinding for the officer\'s report:\n  "{sentence}"')
    print("  Caveat: 20 schools is a small sample, and classrooms are not the same as "
          "class size, teacher numbers or teaching quality.")

    return analysis, r, p, slope, intercept, sentence


def plot_scatter(analysis, r, slope, intercept):
    """One dot per school, coloured by water access, with a trend line."""
    fig, ax = plt.subplots(figsize=(10.5, 6.5))

    colours = {"Yes": "#2E75B6", "No": "#C55A11", "Not reported": "#7F7F7F"}
    for label, group in analysis.groupby(WATER):
        ax.scatter(group[CLASSROOMS], group[ATTENDANCE], s=70,
                   color=colours.get(label, "#7F7F7F"),
                   edgecolor="white", linewidth=0.8, zorder=3,
                   label=f"Water access: {label} ({len(group)})")

    x = analysis[CLASSROOMS].to_numpy()
    trend_x = np.linspace(x.min(), x.max(), 50)
    trend_y = slope * trend_x + intercept
    ax.plot(trend_x, trend_y, color="#1F4E79", linestyle="--", linewidth=1.8,
            label=f"Trend: {slope:+.1f} points per classroom")

    fig.suptitle("Kisumu Schools: Attendance vs Classrooms", fontsize=15, y=0.98)
    fig.text(0.5, 0.925,
             "Each dot is one school. Does more infrastructure come with better attendance?",
             ha="center", fontsize=10.5, color="#444444")

    ax.set_xlabel("Number of classrooms")
    ax.set_ylabel("Average attendance (%)")
    ax.set_ylim(60, 100)
    ax.grid(True, alpha=0.25)
    ax.set_axisbelow(True)

    summary = f"r = {r:.2f}\nn = {len(analysis)} schools"
    ax.text(0.02, 0.97, summary, transform=ax.transAxes, va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#BFBFBF"))

    ax.legend(loc="lower right", frameon=False, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(CHART_PATH, dpi=150)
    plt.close(fig)


def main():
    attendance_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ATTENDANCE
    infrastructure_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INFRASTRUCTURE

    try:
        attendance = load_file(attendance_path, ["school", ATTENDANCE, "county"])
        infrastructure = load_file(infrastructure_path, ["school_name", CLASSROOMS, WATER])

        print("Data quality")
        attendance = clean_attendance(attendance)
        infrastructure = clean_infrastructure(infrastructure)

        merged = merge_files(attendance, infrastructure)
        analysis, r, p, slope, intercept, sentence = analyse(merged)
        plot_scatter(analysis, r, slope, intercept)
    except DataError as error:
        sys.exit(f"Can't complete the analysis. {error}")

    print(f"\nChart saved: {CHART_PATH.name}")


if __name__ == "__main__":
    main()
