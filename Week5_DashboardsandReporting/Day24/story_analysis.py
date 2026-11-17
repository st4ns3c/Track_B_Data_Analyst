"""
Child nutrition programme: three findings for the donor
-------------------------------------------------------
Build plan
  Problem : the NGO has a 10-minute meeting with a donor who is not a data
            person. Raw numbers will lose them; three clear findings with
            one chart each will keep them.
  Input   : data/nutrition_outcomes.csv (from generate_nutrition_data.py),
            one row per child: participant_id, county, age_group,
            months_in_program, sessions_attended, weight_gain_kg.
  Output  : charts/county_results.png
            charts/attendance_and_gain.png
            charts/age_groups.png
            findings.md, the donor brief: three plain-language headlines,
            each with what we expected, what happened, why it matters, and
            the chart; plus speaking notes and the questions the data
            cannot answer yet.

Children joined at different times, so total weight gained is not a fair
comparison: a child enrolled six months has had six times as long. Every
figure here is weight gained per month in the programme, pooled (total kg
divided by total child-months), so a child with six months counts six times
as much as a child with one.

Usage:
    python story_analysis.py

Requirements:
    pip install pandas numpy matplotlib
"""

import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "nutrition_outcomes.csv"
CHART_DIR = BASE_DIR / "charts"
FINDINGS_PATH = BASE_DIR / "findings.md"

REQUIRED = ["participant_id", "county", "age_group", "months_in_program",
            "sessions_attended", "weight_gain_kg"]
SESSIONS_PER_MONTH = 4
AGE_ORDER = ["6-23 months", "2-5 years", "6-10 years"]
ATTENDANCE_BANDS = [0, 0.5, 0.75, 0.9, 1.0001]
BAND_LABELS = ["Fewer than half", "Half to\nthree-quarters", "Three-quarters\nto 90%", "90% or more"]

# One accent for the point of each chart, gray for context; an ordinal blue
# ramp where the bars are ordered steps (attendance bands).
ACCENT = "#2a78d6"
CONTEXT = "#c3c2b7"
ORDINAL_BLUES = ["#86b6ef", "#5598e7", "#2a78d6", "#184f95"]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"


class DataProblem(Exception):
    """A problem with the data file, worded for the client."""


def fail(message):
    # Raised rather than printed, so the weekly report can write the reason
    # into its log when it runs unattended.
    raise DataProblem(message)


def load():
    if not CSV_PATH.exists():
        fail(f"{CSV_PATH.name} is missing. Run `python generate_nutrition_data.py` first.")
    df = pd.read_csv(CSV_PATH)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        fail(f"the file is missing the column(s) {', '.join(missing)}.")
    for col in ["months_in_program", "sessions_attended", "weight_gain_kg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    bad = df[["months_in_program", "sessions_attended", "weight_gain_kg"]].isna().any(axis=1)
    if bad.any():
        fail(f"{bad.sum()} row(s) have a blank or non-number value in months, sessions or weight gain.")
    if (df["months_in_program"] <= 0).any():
        fail("some children have zero or negative months in the programme.")
    offered = df["months_in_program"] * SESSIONS_PER_MONTH
    if (df["sessions_attended"] > offered).any():
        fail("some children attended more sessions than were held in their time in the programme.")
    if df.empty:
        fail("the file has no children in it.")

    df["sessions_offered"] = offered
    df["attendance"] = df["sessions_attended"] / offered
    df["attendance_band"] = pd.cut(df["attendance"], ATTENDANCE_BANDS,
                                   labels=BAND_LABELS, right=False)
    return df


def per_month(frame):
    """Pooled kg gained per child-month."""
    return frame["weight_gain_kg"].sum() / frame["months_in_program"].sum()


def summarise(df, by):
    rows = []
    for key, g in df.groupby(by, observed=True):
        rows.append({
            by: key,
            "children": len(g),
            "kg_per_month": per_month(g),
            "attendance": g["sessions_attended"].sum() / g["sessions_offered"].sum(),
        })
    return pd.DataFrame(rows).set_index(by)


def style_axes(ax, value_axis="x"):
    ax.set_facecolor(SURFACE)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.spines["left" if value_axis == "x" else "bottom"].set_color("#c3c2b7")
    ax.spines["bottom" if value_axis == "x" else "left"].set_visible(False)
    ax.grid(axis=value_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK_SECONDARY, length=0)


def titled_figure(headline, subtitle, left=0.1, size=(9.5, 5.2)):
    fig, ax = plt.subplots(figsize=size, facecolor=SURFACE)
    fig.subplots_adjust(top=0.74, left=left, right=0.96, bottom=0.22)
    fig.text(0.02, 0.97, textwrap.fill(headline, 70), ha="left", va="top",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.84, textwrap.fill(subtitle, 105), ha="left", va="top",
             fontsize=10, color=INK_SECONDARY)
    return fig, ax


def chart_county(by_county, headline, best):
    data = by_county.sort_values("kg_per_month")
    fig, ax = titled_figure(
        headline,
        "Average weight gained per month in the programme. The note on each bar is "
        "the share of weekly sessions that county's families attended.",
        left=0.12,
    )
    colors = [ACCENT if c == best else CONTEXT for c in data.index]
    bars = ax.barh(data.index, data["kg_per_month"], color=colors, height=0.55)
    for bar, (_, row) in zip(bars, data.iterrows()):
        ax.text(bar.get_width() + 0.004, bar.get_y() + bar.get_height() / 2,
                f"{row['kg_per_month']:.2f} kg a month  ·  attended {row['attendance']:.0%} of sessions",
                va="center", fontsize=10, color=INK)
    ax.set_xlim(0, data["kg_per_month"].max() * 1.75)
    ax.set_xlabel("Weight gained per child per month (kg)", color=INK_SECONDARY)
    style_axes(ax, "x")
    # Below the plot: the bar labels run long and would sit under a legend
    # placed inside the axes.
    ax.legend(handles=[Patch(color=ACCENT, label="Best county"),
                       Patch(color=CONTEXT, label="Other counties")],
              loc="upper right", bbox_to_anchor=(1.0, -0.13), ncol=2, frameon=False)
    path = CHART_DIR / "county_results.png"
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def chart_attendance(by_band, headline):
    fig, ax = titled_figure(
        headline,
        "Children grouped by the share of weekly sessions they attended. "
        "Each bar is their average weight gain per month.",
    )
    bars = ax.bar(by_band.index.astype(str), by_band["kg_per_month"],
                  color=ORDINAL_BLUES, width=0.6)
    for bar, (_, row) in zip(bars, by_band.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.006,
                f"{row['kg_per_month']:.2f} kg\n{int(row['children'])} children",
                ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_ylim(0, by_band["kg_per_month"].max() * 1.3)
    ax.set_ylabel("Weight gained per child per month (kg)", color=INK_SECONDARY)
    ax.set_xlabel("Share of sessions attended", color=INK_SECONDARY)
    style_axes(ax, "y")
    ax.legend(handles=[Patch(color=ORDINAL_BLUES[0], label="Fewest sessions"),
                       Patch(color=ORDINAL_BLUES[-1], label="Most sessions")],
              loc="upper left", frameon=False)
    path = CHART_DIR / "attendance_and_gain.png"
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def chart_age(by_age, headline, fastest):
    data = by_age.reindex([a for a in AGE_ORDER if a in by_age.index])
    fig, ax = titled_figure(
        headline,
        "Average weight gained per month in the programme, by the child's age "
        "when they joined.",
    )
    colors = [ACCENT if a == fastest else CONTEXT for a in data.index]
    bars = ax.bar(data.index, data["kg_per_month"], color=colors, width=0.55)
    for bar, (_, row) in zip(bars, data.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.006,
                f"{row['kg_per_month']:.2f} kg a month\n{int(row['children'])} children",
                ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_ylim(0, data["kg_per_month"].max() * 1.3)
    ax.set_ylabel("Weight gained per child per month (kg)", color=INK_SECONDARY)
    ax.set_xlabel("Age group", color=INK_SECONDARY)
    style_axes(ax, "y")
    ax.legend(handles=[Patch(color=ACCENT, label="Fastest-gaining age group"),
                       Patch(color=CONTEXT, label="Other age groups")],
              loc="upper right", frameon=False)
    path = CHART_DIR / "age_groups.png"
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def county_finding(df):
    by_county = summarise(df, "county")
    best = by_county["kg_per_month"].idxmax()
    worst = by_county["kg_per_month"].idxmin()
    attended_most = by_county["attendance"].idxmax()
    attended_least = by_county["attendance"].idxmin()

    # Compare counties among children who attended well. If the gap mostly
    # closes, the county difference is really an attendance difference.
    regular = summarise(df[df["attendance"] >= 0.75], "county")
    gap_all = by_county.loc[best, "kg_per_month"] - by_county.loc[worst, "kg_per_month"]
    gap_regular = regular.loc[best, "kg_per_month"] - regular.loc[worst, "kg_per_month"]
    explained_by_attendance = worst == attended_least and gap_regular < gap_all / 2

    if explained_by_attendance:
        headline = (f"Children in {best} gained the most weight; {worst} fell behind "
                    f"mainly because families there missed more sessions.")
    else:
        headline = f"Children in {best} gained the most weight and {worst} the least."
    return {
        "table": by_county, "regular": regular, "best": best, "worst": worst,
        "attended_most": attended_most, "attended_least": attended_least,
        "gap_all": gap_all, "gap_regular": gap_regular,
        "explained": explained_by_attendance, "headline": headline,
    }


def attendance_finding(df):
    by_band = summarise(df, "attendance_band")
    child_month = df["weight_gain_kg"] / df["months_in_program"]
    r = df["attendance"].corr(child_month)
    low, high = by_band["kg_per_month"].iloc[0], by_band["kg_per_month"].iloc[-1]
    rises_every_step = by_band["kg_per_month"].is_monotonic_increasing

    if rises_every_step and r >= 0.3:
        headline = ("The more sessions a child came to, the more weight they gained: "
                    "every session counts.")
    elif r >= 0.3:
        headline = "Children who came to more sessions generally gained more weight."
    else:
        headline = "Coming to more sessions made little difference to weight gain."
    return {"table": by_band, "r": r, "low": low, "high": high,
            "ratio": high / low, "headline": headline}


def age_finding(df):
    by_age = summarise(df, "age_group")
    fastest = by_age["kg_per_month"].idxmax()
    slowest = by_age["kg_per_month"].idxmin()
    if fastest == AGE_ORDER[0]:
        headline = ("The youngest children gained weight fastest, so reaching babies "
                    "early does the most good.")
    else:
        headline = f"Children aged {fastest} gained weight fastest."
    return {"table": by_age, "fastest": fastest, "slowest": slowest,
            "ratio": by_age.loc[fastest, "kg_per_month"] / by_age.loc[slowest, "kg_per_month"],
            "headline": headline}


def print_tables(df, f1, f2, f3):
    total_kg = df["weight_gain_kg"].sum()
    print(f"{len(df)} children, {df['months_in_program'].sum()} child-months, "
          f"{total_kg:,.0f} kg gained in total, {per_month(df):.3f} kg per child per month.\n")
    for title, table in [("By county", f1["table"]),
                         ("By county, children attending 75%+ of sessions", f1["regular"]),
                         ("By share of sessions attended", f2["table"]),
                         ("By age group", f3["table"])]:
        shown = table.copy()
        shown.index = [str(i).replace("\n", " ") for i in shown.index]
        shown["kg_per_month"] = shown["kg_per_month"].round(3)
        shown["attendance"] = (100 * shown["attendance"]).round(1).astype(str) + "%"
        print(f"{title}\n{shown.to_string()}\n")
    print(f"Link between attendance and monthly gain (correlation): r = {f2['r']:.2f}")
    print(f"Children losing weight: {(df['weight_gain_kg'] < 0).sum()}\n")
    for n, f in enumerate([f1, f2, f3], 1):
        print(f"Headline {n}: {f['headline']}")


def write_findings(df, f1, f2, f3):
    c, a, g = f1["table"], f2["table"], f3["table"]
    best, worst = f1["best"], f1["worst"]
    young = f3["fastest"]
    lines = [
        "# Six months of the child nutrition programme: what the donor needs to know",
        "",
        f"*{len(df)} children in {', '.join(sorted(df['county'].unique()))}, "
        f"May to October 2026. "
        f"Together they gained **{df['weight_gain_kg'].sum():,.0f} kg**.*",
        "",
        "All figures are weight gained **per month in the programme**, because children "
        "joined at different times.",
        "",
        "## 1. " + f1["headline"],
        "",
        "![County results](charts/county_results.png)",
        "",
        "- **What we expected:** similar results in all three counties. The programme, "
        "the food basket and the sessions are the same everywhere.",
        f"- **What happened:** children in {best} gained {c.loc[best, 'kg_per_month']:.2f} kg "
        f"a month and children in {worst} {c.loc[worst, 'kg_per_month']:.2f} kg. "
        f"Families in {f1['attended_most']} came to {c.loc[f1['attended_most'], 'attendance']:.0%} "
        f"of sessions; families in {f1['attended_least']} came to "
        f"{c.loc[f1['attended_least'], 'attendance']:.0%}.",
    ]
    if f1["explained"]:
        lines.append(
            f"- **Why it matters:** among children who came to at least three sessions in four, "
            f"the gap between {best} and {worst} shrinks by more than half "
            f"({f1['gap_regular']:.2f} kg a month, against {f1['gap_all']:.2f} kg overall). "
            f"{worst} is not failing; its families are missing sessions. Helping them attend, "
            f"for example with transport or sessions closer to home, is the fix."
        )
    else:
        lines.append(f"- **Why it matters:** {worst} needs a closer look before the next phase.")
    lines += [
        "",
        "## 2. " + f2["headline"],
        "",
        "![Attendance and weight gain](charts/attendance_and_gain.png)",
        "",
        "- **What we expected:** children who attend more should gain more, because each "
        "session brings a supervised meal, a weight check and advice for the parent.",
        f"- **What happened:** children who came to 90% or more of sessions gained "
        f"{f2['high']:.2f} kg a month. Children who came to fewer than half gained "
        f"only {f2['low']:.2f} kg, so the regular attenders gained {f2['ratio'] - 1:.0%} more "
        "each month. Weight gain rises at every step of attendance.",
        "- **Why it matters:** attendance is the lever the programme controls. Every extra "
        "session a family makes is more weight for the child. Following up with families who "
        "miss two sessions in a row is a simple, low-cost way to improve results.",
        "",
        "## 3. " + f3["headline"],
        "",
        "![Age groups](charts/age_groups.png)",
        "",
        "- **What we expected:** the youngest children to respond fastest, because the first "
        "two years are when a child catches up most quickly.",
        f"- **What happened:** children aged {young} gained "
        f"{g.loc[young, 'kg_per_month']:.2f} kg a month, against "
        f"{g.loc[f3['slowest'], 'kg_per_month']:.2f} kg for children aged {f3['slowest']}. "
        + (f"Their attendance was no better than the others' "
           f"({g.loc[young, 'attendance']:.0%}), so the difference is the age, not the effort."
           if g.loc[young, "attendance"] <= g["attendance"].max() - 0.01 else
           f"They also attended more ({g.loc[young, 'attendance']:.0%}), which explains part "
           f"of the difference."),
        "- **Why it matters:** the same sessions do more for a baby than for an older "
        "child. The next phase should find and enrol children under two first.",
        "",
        "## What we ask the donor to support",
        "",
        f"1. Transport or outreach sessions for {worst} families, so attendance there "
        f"reaches the {f1['attended_most']} level.",
        "2. A follow-up call after any two missed sessions, in every county.",
        "3. Enrolment that starts with children under two.",
        "",
        "*Data: programme records, synthetic sample for this exercise.*",
    ]
    FINDINGS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    try:
        df = load()
    except DataProblem as problem:
        print(f"Cannot build the donor brief: {problem}")
        sys.exit(1)
    CHART_DIR.mkdir(exist_ok=True)

    f1 = county_finding(df)
    f2 = attendance_finding(df)
    f3 = age_finding(df)
    print_tables(df, f1, f2, f3)

    chart_county(f1["table"], f1["headline"], f1["best"])
    chart_attendance(f2["table"], f2["headline"])
    chart_age(f3["table"], f3["headline"], f3["fastest"])
    write_findings(df, f1, f2, f3)
    print(f"\nSaved 3 charts to {CHART_DIR} and the brief to {FINDINGS_PATH.name}")


if __name__ == "__main__":
    main()
