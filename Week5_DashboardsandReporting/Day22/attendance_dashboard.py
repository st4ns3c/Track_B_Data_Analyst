"""
Nakuru school attendance dashboard
----------------------------------
Build plan
  Problem : a school principal in Nakuru wants to see attendance every
            morning on her phone or laptop, without opening Excel.
  Input   : a CSV of daily attendance, one row per class per school day:
            date, class_name, students_present, students_total.
            The school file data/attendance.csv loads by default. A class
            teacher drags in their own sheet and the page updates at once.
  Output  : a web page with a class dropdown and a date range picker,
            three headline numbers, a line chart per class, a table that
            flags falling attendance, and a download of the filtered view.
            "All classes" shows the overall rate and the best and worst
            class; one class shows its rate, its lowest day and the
            pupil-days lost, with a week-by-week table.

Usage:
    streamlit run attendance_dashboard.py

Requirements:
    pip install streamlit pandas
"""

import io
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
    """A problem with the attendance file, worded for the principal or a teacher."""


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


# Cached on the file's bytes, so changing a filter does not re-read the
# upload, but a new or edited file is read fresh.
@st.cache_data
def load_upload(content):
    try:
        raw = pd.read_csv(io.BytesIO(content))
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


def weekly_table(period):
    """Week-by-week figures for one class, Monday-start weeks."""
    weeks = period.assign(week=period["date"].dt.to_period("W-SUN").dt.start_time)
    table = weeks.groupby("week").agg(
        days=("date", "nunique"),
        present=("students_present", "sum"),
        total=("students_total", "sum"),
    ).reset_index()
    table["Attendance"] = 100 * table["present"] / table["total"]
    table["Pupil-days absent"] = table["total"] - table["present"]
    table["Week starting"] = table["week"].dt.strftime("%a %d %b %Y")
    return table.rename(columns={"days": "School days"})[
        ["Week starting", "School days", "Attendance", "Pupil-days absent"]
    ]


def download_csv(period):
    """The filtered rows in the same layout as the upload, plus the rate."""
    out = period.sort_values(["date", "class_name"]).copy()
    out["attendance_pct"] = (100 * out["students_present"] / out["students_total"]).round(1)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False).encode("utf-8")


def file_slug(text):
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")


def main():
    st.set_page_config(page_title="School Attendance", page_icon="🏫", layout="centered")
    st.title("School attendance")

    uploaded = st.file_uploader(
        "Upload an attendance CSV (drag the file here)",
        type=["csv"],
        help="Columns needed: date, class_name, students_present, students_total. "
             "Other columns are ignored.",
    )

    try:
        df = load_upload(uploaded.getvalue()) if uploaded else load_sample()
    except FileNotFoundError:
        st.error(
            "The sample file data/attendance.csv is missing. Run "
            "`python generate_attendance_data.py` to create it, or upload a CSV above."
        )
        st.stop()
    except DataProblem as problem:
        st.error(f"**{uploaded.name}**: {problem}" if uploaded else str(problem))
        st.stop()

    classes = sorted(df["class_name"].unique())
    source = f"**{uploaded.name}**" if uploaded else "the school sample data"
    st.caption(
        f"Showing {source}: {len(classes)} "
        f"{'class' if len(classes) == 1 else 'classes'}, "
        f"{df['date'].nunique()} school days."
    )

    # Keying the filters on the file means a new upload starts them fresh,
    # instead of keeping a class or dates that the new file does not have.
    data_key = uploaded.file_id if uploaded else "sample"
    first_day = df["date"].min().date()
    last_day = df["date"].max().date()
    default_start = max(first_day, last_day - timedelta(days=DEFAULT_WINDOW_DAYS - 1))

    col_a, col_b = st.columns(2)
    options = ["All classes"] + classes if len(classes) > 1 else classes
    choice = col_a.selectbox("Class", options, key=f"class-{data_key}")
    dates = col_b.date_input(
        "Dates",
        value=(default_start, last_day),
        min_value=first_day,
        max_value=last_day,
        format="DD/MM/YYYY",
        key=f"dates-{data_key}",
        help="Opens on the last 30 days in the file. Pick a start date, then an end date.",
    )
    if len(dates) != 2:
        st.info("Now pick the end date.")
        st.stop()
    start, end = dates

    one_class = choice != "All classes"
    subset = df[df["class_name"] == choice] if one_class else df
    period = subset[subset["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
    if period.empty:
        st.warning(f"{choice} has no school days between those dates. Widen the dates.")
        st.stop()

    # Compare with the same number of calendar days just before the range.
    length = (end - start).days + 1
    before = subset[subset["date"].between(
        pd.Timestamp(start - timedelta(days=length)), pd.Timestamp(start - timedelta(days=1))
    )]

    table = class_table(period)
    overall = rate(period)
    delta = f"{overall - rate(before):+.1f} pts" if not before.empty else None
    delta_help = f"The change compares this range with the {length} days just before it."

    # The class-name cards get more room so a stream name like
    # "Grade 8 West" is not cut off on a laptop.
    col1, col2, col3 = st.columns([1, 1.35, 1.35])
    if one_class:
        daily = period.assign(day_rate=100 * period["students_present"] / period["students_total"])
        low = daily.loc[daily["day_rate"].idxmin()]
        absent = int(period["students_total"].sum() - period["students_present"].sum())
        col1.metric(f"{choice} attendance", f"{overall:.1f}%", delta=delta,
                    help=delta_help, border=True)
        col2.metric("Lowest day", f"{low['date']:%a %d %b}",
                    delta_description=f"{low['day_rate']:.1f}% present", border=True)
        col3.metric("Pupil-days absent", f"{absent:,}",
                    delta_description=f"over {period['date'].nunique()} school days",
                    border=True)
    else:
        best, worst = table.iloc[0], table.iloc[-1]
        col1.metric("Overall attendance", f"{overall:.1f}%", delta=delta,
                    help=delta_help, border=True)
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

    st.download_button(
        "Download this view as CSV",
        data=download_csv(period),
        file_name=f"attendance_{file_slug(choice)}_{start:%Y-%m-%d}_to_{end:%Y-%m-%d}.csv",
        mime="text/csv",
        icon=":material/download:",
        on_click="ignore",
        help=f"{len(period)} rows: the class and dates chosen above.",
    )

    st.subheader(f"{choice if one_class else 'Attendance by class'} over time")
    weekly = st.toggle(
        "Show weekly averages",
        help="Weekly averages smooth out single bad days, so a steady decline is easier to see.",
    )
    st.altair_chart(trend_chart(period, weekly), width="stretch")

    if one_class:
        st.subheader(f"{choice}, week by week")
        st.dataframe(
            weekly_table(period),
            hide_index=True,
            width="stretch",
            column_config={"Attendance": st.column_config.NumberColumn(format="%.1f%%")},
        )
    else:
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

    with st.expander("Daily records in this view"):
        records = period.sort_values(["date", "class_name"]).assign(
            attendance=lambda d: (100 * d["students_present"] / d["students_total"]).round(1)
        )
        records["date"] = records["date"].dt.strftime("%a %d %b %Y")
        st.dataframe(records, hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
