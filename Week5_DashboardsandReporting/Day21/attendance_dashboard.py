"""
Nakuru school attendance dashboard
----------------------------------
Build plan
  Problem : a school principal in Nakuru wants to see attendance every
            morning on her phone or laptop, without opening Excel.
  Input   : a CSV of daily attendance, one row per class per school day:
            date, class_name, students_present, students_total.
            The sample file data/attendance.csv loads by default; the
            principal can upload the school's own file in the sidebar.
  Output  : a web page with three headline numbers (overall rate,
            best-attending class, worst-attending class), a date-range
            slider, a line chart of attendance per class, and a class table
            that flags any class whose attendance is falling.

Usage:
    streamlit run attendance_dashboard.py

Requirements:
    pip install streamlit pandas
"""

from datetime import timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
SAMPLE_CSV = BASE_DIR / "data" / "attendance.csv"

REQUIRED_COLUMNS = ["date", "class_name", "students_present", "students_total"]
DEFAULT_WINDOW_DAYS = 30
# A class counts as falling when the second half of the chosen period is at
# least this many percentage points below the first half. Smaller moves are
# within the normal day-to-day noise of a class of about 45 students.
FALLING_THRESHOLD = 2.0


class DataProblem(Exception):
    """A problem with the attendance file, worded for the principal."""


def clean(raw):
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise DataProblem(
            f"The file is missing the column(s): {', '.join(missing)}. "
            f"It needs these four columns: {', '.join(REQUIRED_COLUMNS)}."
        )
    df = raw[REQUIRED_COLUMNS].copy()
    if df.empty:
        raise DataProblem("The file has the right columns but no attendance rows.")

    # ISO dates first; anything else is read day first, because Excel in Kenya
    # writes 01/10/2026 for 1 October.
    text = df["date"].astype(str).str.strip()
    iso = pd.to_datetime(text, errors="coerce", format="ISO8601")
    other = pd.to_datetime(text[iso.isna()], errors="coerce", format="mixed", dayfirst=True)
    df["date"] = iso.fillna(other)
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        raise DataProblem(
            f"{bad_dates} row(s) have a date that could not be read. "
            "Please write dates as YYYY-MM-DD, for example 2026-10-30."
        )
    df["date"] = df["date"].dt.normalize()

    for col in ["students_present", "students_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise DataProblem(
                f"Some rows have a blank or non-number value in '{col}'. "
                "Every row needs a whole number there."
            )
    if (df["students_total"] <= 0).any():
        raise DataProblem("Some rows have a class size (students_total) of zero or less.")
    if (df["students_present"] < 0).any():
        raise DataProblem("Some rows have a negative number of students present.")
    over = df["students_present"] > df["students_total"]
    if over.any():
        first = df[over].iloc[0]
        raise DataProblem(
            f"{over.sum()} row(s) have more students present than on the register, "
            f"for example {first['class_name']} on {first['date']:%d %b %Y}."
        )

    df["class_name"] = df["class_name"].astype(str).str.strip()
    # If a class was entered twice for one day, add the two entries together
    # rather than counting the day twice in the chart.
    return (
        df.groupby(["date", "class_name"], as_index=False)[
            ["students_present", "students_total"]
        ].sum()
    )


@st.cache_data
def load_sample():
    return clean(pd.read_csv(SAMPLE_CSV))


def load_upload(uploaded):
    try:
        raw = pd.read_csv(uploaded)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise DataProblem(
            "That file could not be read as a CSV. In Excel, use "
            "File > Save As > CSV (Comma delimited) and upload it again."
        )
    return clean(raw)


def rate(frame):
    """Attendance rate in percent. Sums first, so a big class weighs more than a small one."""
    total = frame["students_total"].sum()
    return 100 * frame["students_present"].sum() / total if total else float("nan")


def class_table(period):
    """Rate per class over the period, and the change from its first half to its second."""
    days = sorted(period["date"].unique())
    first_half = period[period["date"].isin(days[: len(days) // 2])]
    second_half = period[period["date"].isin(days[len(days) // 2 :])]

    rows = []
    for name, group in period.groupby("class_name"):
        change = rate(second_half[second_half["class_name"] == name]) - rate(
            first_half[first_half["class_name"] == name]
        )
        rows.append({
            "Class": name,
            "Attendance": rate(group),
            "Change": change,
            "Days absent (pupil-days)": int(
                group["students_total"].sum() - group["students_present"].sum()
            ),
        })
    table = pd.DataFrame(rows).sort_values("Attendance", ascending=False)
    table["Trend"] = table["Change"].apply(
        lambda c: "Falling" if c <= -FALLING_THRESHOLD
        else "Rising" if c >= FALLING_THRESHOLD
        else "Steady" if pd.notna(c)
        else "Not enough days"
    )
    return table.reset_index(drop=True)


def trend_chart(period, weekly):
    data = period.copy()
    if weekly:
        # Label each week by its Monday so the axis reads as school weeks.
        data["date"] = data["date"].dt.to_period("W-SUN").dt.start_time
    data = data.groupby(["date", "class_name"], as_index=False)[
        ["students_present", "students_total"]
    ].sum()
    data["Attendance (%)"] = 100 * data["students_present"] / data["students_total"]

    low = max(0, data["Attendance (%)"].min() - 3)
    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Week starting" if weekly else "School day",
                    axis=alt.Axis(format="%d %b")),
            y=alt.Y("Attendance (%):Q", title="Attendance (%)",
                    scale=alt.Scale(domain=[low, 100])),
            color=alt.Color("class_name:N", title="Class",
                            scale=alt.Scale(scheme="tableau10"),
                            legend=alt.Legend(orient="bottom", columns=3)),
            tooltip=[
                alt.Tooltip("date:T", title="Week of" if weekly else "Date",
                            format="%a %d %b %Y"),
                alt.Tooltip("class_name:N", title="Class"),
                alt.Tooltip("Attendance (%):Q", format=".1f"),
                alt.Tooltip("students_present:Q", title="Present"),
                alt.Tooltip("students_total:Q", title="On register"),
            ],
        )
        .properties(height=380, width="container")
        .interactive(bind_y=False)
    )


def main():
    st.set_page_config(page_title="School Attendance", page_icon="🏫", layout="centered")
    st.title("School attendance")

    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader(
            "Upload this term's attendance CSV",
            type=["csv"],
            help="Columns needed: date, class_name, students_present, students_total.",
        )

    try:
        df = load_upload(uploaded) if uploaded else load_sample()
    except FileNotFoundError:
        st.error(
            "The sample file data/attendance.csv is missing. Run "
            "`python generate_attendance_data.py` to create it, or upload a CSV "
            "in the sidebar."
        )
        st.stop()
    except DataProblem as problem:
        st.error(str(problem))
        st.stop()

    source = f"your file **{uploaded.name}**" if uploaded else "the sample data"
    st.caption(
        f"Showing {source}: {df['class_name'].nunique()} classes, "
        f"{df['date'].nunique()} school days. Upload your own file in the sidebar."
    )

    first_day = df["date"].min().date()
    last_day = df["date"].max().date()
    default_start = max(first_day, last_day - timedelta(days=DEFAULT_WINDOW_DAYS - 1))
    if first_day == last_day:
        start, end = first_day, last_day
    else:
        start, end = st.slider(
            "Date range",
            min_value=first_day,
            max_value=last_day,
            value=(default_start, last_day),
            format="DD MMM YYYY",
            help="Starts on the last 30 days. Drag either end to change it.",
        )

    in_range = df["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    period = df[in_range]
    if period.empty:
        st.warning("There are no school days in that range. Widen the dates.")
        st.stop()

    # Compare with the same number of calendar days just before the range.
    length = (end - start).days + 1
    before = df[df["date"].between(
        pd.Timestamp(start - timedelta(days=length)), pd.Timestamp(start - timedelta(days=1))
    )]

    table = class_table(period)
    best, worst = table.iloc[0], table.iloc[-1]
    overall = rate(period)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Overall attendance",
        f"{overall:.1f}%",
        delta=f"{overall - rate(before):+.1f} pts" if not before.empty else None,
        help=f"The change compares this range with the {length} days just before it.",
        border=True,
    )
    col2.metric("Best-attending class", best["Class"],
                delta_description=f"{best['Attendance']:.1f}% attendance", border=True)
    col3.metric("Worst-attending class", worst["Class"],
                delta_description=f"{worst['Attendance']:.1f}% attendance", border=True)

    falling = table[table["Trend"] == "Falling"]
    if not falling.empty:
        names = ", ".join(
            f"**{r.Class}** ({r.Change:+.1f} pts)" for r in falling.itertuples()
        )
        st.warning(
            f"Falling attendance: {names}, comparing the second half of this "
            "period with the first half."
        )

    st.subheader("Attendance by class over time")
    weekly = st.toggle(
        "Show weekly averages",
        help="Weekly averages smooth out single bad days, so a steady decline is easier to see.",
    )
    st.altair_chart(trend_chart(period, weekly), width="stretch")

    st.subheader(f"Classes, {start:%d %b} to {end:%d %b %Y}")
    st.dataframe(
        table[["Class", "Attendance", "Change", "Trend", "Days absent (pupil-days)"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Attendance": st.column_config.NumberColumn(format="%.1f%%"),
            "Change": st.column_config.NumberColumn(
                "Change (pts)", format="%+.1f",
                help="Second half of the period minus the first half, in percentage points.",
            ),
        },
    )

    with st.expander("Daily records in this range"):
        records = period.sort_values(["date", "class_name"]).assign(
            attendance=lambda d: (100 * d["students_present"] / d["students_total"]).round(1)
        )
        records["date"] = records["date"].dt.strftime("%a %d %b %Y")
        st.dataframe(records, hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
