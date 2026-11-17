"""
M-Pesa Business Tracker
-----------------------
Build plan
  Problem : a small business takes most of its sales on M-Pesa. The owner
            wants to see daily takings, where the money goes and the weekly
            trend, without reading the statement line by line.
  Input   : an M-Pesa business statement as CSV. The sample
            (data/mpesa_statement.csv, a cafe's till) loads by default; the
            owner can upload their own. Needed columns: Completion Time,
            Details, Transaction Status, Paid In, Withdrawn. Reason Type is
            used when present; otherwise each line is sorted by its Details.
  Output  : a Streamlit page with a date range and a transaction-type
            filter, four headline numbers, daily sales, the top transaction
            types, the weekly trend of sales against spending, the busiest
            hours, and the filtered statement as a download.

Only completed transactions count. Failed payments are listed but never
added to sales, and reversals are taken off sales. Money moved to the
owner's own bank account is shown, but not counted as spending.

Usage:
    streamlit run app.py

Requirements:
    pip install -r requirements.txt
"""

import io
from datetime import timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
SAMPLE_CSV = BASE_DIR / "data" / "mpesa_statement.csv"
REQUIRED = ["Completion Time", "Details", "Transaction Status", "Paid In", "Withdrawn"]

SALES = "Customer Payment"
BANK = "Bank Transfer"
REVERSAL = "Reversal"
# Types that are the cost of running the business.
SPENDING = ["Supplier Payment", "Salary Payment", "Utility Payment", "Merchant Charge",
            "Other Money Out"]

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRAY = "#c3c2b7"


class StatementProblem(Exception):
    """A problem with the statement file, worded for the business owner."""


def classify(details, paid_in):
    """Sort a statement line by its description, for statements without Reason Type."""
    text = str(details).lower()
    if "reversal" in text:
        return REVERSAL
    if "charge" in text:
        return "Merchant Charge"
    if "salary" in text:
        return "Salary Payment"
    if "bank" in text:
        return BANK
    if "token" in text or "electric" in text or "water" in text:
        return "Utility Payment"
    if "pay bill" in text or "paybill" in text:
        return "Supplier Payment"
    if paid_in > 0 or "payment from" in text or "received" in text:
        return SALES
    return "Other Money Out"


def to_number(series):
    # Exports often write 1,250.00 or leave a blank for zero.
    # Fill blanks first: in pandas 3 a blank stays missing after astype(str).
    cleaned = series.astype(object).where(series.notna(), "0").astype(str)
    cleaned = cleaned.str.replace(",", "", regex=False).str.strip().replace({"": "0"})
    return pd.to_numeric(cleaned, errors="coerce")


def clean(raw):
    raw.columns = [str(c).strip() for c in raw.columns]
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise StatementProblem(
            f"This file is missing the column(s): {', '.join(missing)}. An M-Pesa business "
            f"statement export needs: {', '.join(REQUIRED)}."
        )
    df = raw.copy()
    df["time"] = pd.to_datetime(df["Completion Time"], errors="coerce", dayfirst=False, format="mixed")
    bad_time = df["time"].isna().sum()
    if bad_time:
        raise StatementProblem(f"{bad_time} line(s) have a Completion Time that could not be read.")
    for col in ["Paid In", "Withdrawn"]:
        df[col] = to_number(df[col]).abs()
        if df[col].isna().any():
            raise StatementProblem(f"Some lines have a {col} amount that is not a number.")
    if df.empty:
        raise StatementProblem("The statement has no transactions in it.")

    if "Reason Type" in df.columns:
        df["type"] = df["Reason Type"].fillna("").astype(str).str.strip()
        blank = df["type"].eq("")
        df.loc[blank, "type"] = [classify(d, p) for d, p in zip(df.loc[blank, "Details"], df.loc[blank, "Paid In"])]
    else:
        df["type"] = [classify(d, p) for d, p in zip(df["Details"], df["Paid In"])]
    df["completed"] = df["Transaction Status"].astype(str).str.strip().str.lower().eq("completed")
    df["amount"] = df["Paid In"] - df["Withdrawn"]
    df["date"] = df["time"].dt.normalize()
    return df.sort_values("time").reset_index(drop=True)


@st.cache_data
def load_sample():
    if not SAMPLE_CSV.exists():
        raise StatementProblem("The sample statement is missing. Run "
                               "`python generate_mpesa_statement.py`, or upload a statement.")
    return clean(pd.read_csv(SAMPLE_CSV))


@st.cache_data
def load_upload(content):
    try:
        raw = pd.read_csv(io.BytesIO(content))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise StatementProblem("That file could not be read as a CSV. Download the statement as CSV "
                               "(or open it in Excel and use File > Save As > CSV), then upload it again.")
    return clean(raw)


def kes(value):
    # Millions are shortened so the headline cards never cut a number off.
    if abs(value) >= 1_000_000:
        return f"KES {value / 1_000_000:,.2f}M"
    return f"KES {value:,.0f}"


def totals(done):
    sales_lines = done[done["type"] == SALES]
    sales = sales_lines["Paid In"].sum() - done.loc[done["type"] == REVERSAL, "Withdrawn"].sum()
    return {
        "sales": sales,
        "payments": len(sales_lines),
        "average": sales_lines["Paid In"].mean() if len(sales_lines) else 0,
        "spending": done.loc[done["type"].isin(SPENDING), "Withdrawn"].sum(),
        "to_bank": done.loc[done["type"] == BANK, "Withdrawn"].sum(),
    }


def daily_sales_chart(done, start, end):
    days = pd.date_range(start, end, freq="D")
    daily = (done[done["type"] == SALES].groupby("date")["Paid In"].sum()
             .reindex(days, fill_value=0).rename_axis("date").reset_index(name="sales"))
    daily["day"] = daily["date"].dt.strftime("%A")
    daily["average"] = daily["sales"].rolling(7, min_periods=1).mean()
    base = alt.Chart(daily).encode(x=alt.X("date:T", title=None, axis=alt.Axis(format="%d %b")))
    bars = base.mark_bar(color=BLUE, opacity=0.85).encode(
        y=alt.Y("sales:Q", title="Sales (KES)", axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("date:T", title="Day", format="%A %d %B"),
                 alt.Tooltip("sales:Q", title="Sales (KES)", format=",.0f")])
    line = base.mark_line(color="#0b0b0b", strokeWidth=2).encode(
        y="average:Q",
        tooltip=[alt.Tooltip("average:Q", title="7-day average (KES)", format=",.0f")])
    return (bars + line).properties(height=300)


def types_chart(done):
    by_type = done.groupby("type").agg(value=("Paid In", "sum"), out=("Withdrawn", "sum"),
                                       count=("type", "size")).reset_index()
    by_type["total"] = by_type["value"] + by_type["out"]
    by_type["direction"] = by_type["value"].gt(by_type["out"]).map({True: "Money in", False: "Money out"})
    by_type = by_type.sort_values("total", ascending=False)
    bars = alt.Chart(by_type).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        x=alt.X("total:Q", title="Value (KES)", axis=alt.Axis(format="~s")),
        # An explicit order: "-x" is not applied once the text layer is added.
        y=alt.Y("type:N", sort=by_type["type"].tolist(), title=None),
        color=alt.Color("direction:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=["Money in", "Money out"], range=[BLUE, ORANGE])),
        tooltip=[alt.Tooltip("type:N", title="Type"),
                 alt.Tooltip("total:Q", title="Value (KES)", format=",.0f"),
                 alt.Tooltip("count:Q", title="Transactions", format=",")])
    labels = bars.mark_text(align="left", dx=4, fontSize=11).encode(
        text=alt.Text("count:Q", format=","), color=alt.value("#52514e"))
    return (bars + labels).properties(height=300)


def weekly_chart(done):
    weeks = done.assign(week=done["date"].dt.to_period("W-SUN").dt.start_time)
    sales = weeks[weeks["type"] == SALES].groupby("week")["Paid In"].sum().rename("Sales")
    spend = weeks[weeks["type"].isin(SPENDING)].groupby("week")["Withdrawn"].sum().rename("Spending")
    data = pd.concat([sales, spend], axis=1).fillna(0).reset_index().melt(
        id_vars="week", var_name="series", value_name="kes")
    return alt.Chart(data).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("week:T", title="Week starting", axis=alt.Axis(format="%d %b")),
        y=alt.Y("kes:Q", title="KES", axis=alt.Axis(format="~s")),
        color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=["Sales", "Spending"], range=[BLUE, ORANGE])),
        tooltip=[alt.Tooltip("week:T", title="Week starting", format="%d %B %Y"),
                 alt.Tooltip("series:N", title=""),
                 alt.Tooltip("kes:Q", title="KES", format=",.0f")],
    ).properties(height=300)


def hours_chart(done):
    sales = done[done["type"] == SALES]
    days = max(1, sales["date"].nunique())
    by_hour = sales.groupby(sales["time"].dt.hour)["Paid In"].sum().div(days).rename_axis("hour").reset_index(name="avg")
    by_hour["label"] = by_hour["hour"].map(lambda h: f"{h:02d}:00")
    peak = by_hour["avg"].idxmax()
    by_hour["peak"] = ["Busiest hour" if i == peak else "Other hours" for i in by_hour.index]
    return alt.Chart(by_hour).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("label:N", title="Hour of the day", sort=None),
        y=alt.Y("avg:Q", title="Average sales per day (KES)", axis=alt.Axis(format="~s")),
        color=alt.Color("peak:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=["Busiest hour", "Other hours"], range=[BLUE, GRAY])),
        tooltip=[alt.Tooltip("label:N", title="Hour"),
                 alt.Tooltip("avg:Q", title="Average sales (KES)", format=",.0f")],
    ).properties(height=300)


def main():
    st.set_page_config(page_title="M-Pesa Business Tracker", page_icon="💚", layout="wide")

    with st.sidebar:
        st.header("Your statement")
        uploaded = st.file_uploader(
            "Upload an M-Pesa business statement (CSV)", type=["csv"],
            help="Needs these columns: " + ", ".join(REQUIRED) + ". Reason Type is used if present.")
        st.caption("Your file stays in this session only. It is not saved anywhere.")

    try:
        df = load_upload(uploaded.getvalue()) if uploaded else load_sample()
    except StatementProblem as problem:
        st.error(f"**{uploaded.name}**: {problem}" if uploaded else str(problem))
        st.stop()

    source = f"your statement **{uploaded.name}**" if uploaded else "a sample statement for Wanjiru's Cafe, Thika Road"
    first, last = df["date"].min().date(), df["date"].max().date()
    st.title("M-Pesa Business Tracker")
    st.markdown(
        "See what came in, what went out and how the week is going, straight from your M-Pesa "
        f"statement. Showing {source}, **{first:%d %B} to {last:%d %B %Y}**. "
        "Upload your own statement in the sidebar."
    )

    key = uploaded.file_id if uploaded else "sample"
    with st.sidebar:
        st.header("Filters")
        dates = st.date_input("Dates", value=(max(first, last - timedelta(days=29)), last),
                              min_value=first, max_value=last, format="DD/MM/YYYY", key=f"d-{key}")
        types = sorted(df["type"].unique())
        chosen = st.multiselect("Transaction types", types, default=types, key=f"t-{key}",
                                help="Applies to the types chart, the weekly trend and the table.")
    if len(dates) != 2:
        st.info("Now pick the end date.")
        st.stop()
    start, end = dates

    in_range = df[df["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
    done = in_range[in_range["completed"]]
    failed = in_range[~in_range["completed"]]
    if done.empty:
        st.warning("No completed transactions between those dates. Widen the dates.")
        st.stop()

    t = totals(done)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sales", kes(t["sales"]), border=True,
              help="Completed customer payments, less any reversals.")
    k2.metric("Customer payments", f"{t['payments']:,}", border=True,
              help=f"Average sale {kes(t['average'])}.")
    k3.metric("Average sale", kes(t["average"]), border=True)
    k4.metric("Spending", kes(t["spending"]), border=True,
              help="Suppliers, wages, bills and M-Pesa charges. Money moved to your own bank is not spending.")
    notes = [f"{(end - start).days + 1} days"]
    if t["to_bank"]:
        notes.append(f"{kes(t['to_bank'])} moved to the bank (your money, not spending)")
    if len(failed):
        notes.append(f"{len(failed)} failed transaction{'s' if len(failed) != 1 else ''}, not counted")
    st.caption(" · ".join(notes))

    filtered = done[done["type"].isin(chosen)]

    left, right = st.columns(2)
    with left:
        st.subheader("Daily sales")
        st.altair_chart(daily_sales_chart(done, start, end), width="stretch")
        st.caption("Bars are each day's customer payments; the black line is the 7-day average.")
    with right:
        st.subheader("Top transaction types")
        if filtered.empty:
            st.info("No transaction types chosen.")
        else:
            st.altair_chart(types_chart(filtered), width="stretch")
            st.caption("Total value of each type. The number at the end of each bar is how many transactions.")

    left, right = st.columns(2)
    with left:
        st.subheader("Weekly trend: sales against spending")
        st.altair_chart(weekly_chart(done), width="stretch")
        st.caption("Spending leaves out money moved to the bank. A first or last week may be "
                   "short if the dates start or end mid-week.")
    with right:
        st.subheader("When customers pay")
        st.altair_chart(hours_chart(done), width="stretch")
        st.caption("Average sales in each hour, per trading day. Plan staff and stock for the busiest hour.")

    with st.expander("See the statement lines"):
        lines = filtered.sort_values("time", ascending=False)
        shown = lines[["time", "Details", "type", "Paid In", "Withdrawn"] +
                      (["Balance"] if "Balance" in lines.columns else [])].rename(
            columns={"time": "Time", "type": "Type"})
        st.dataframe(shown, hide_index=True, width="stretch",
                     column_config={"Time": st.column_config.DatetimeColumn(format="ddd D MMM, HH:mm")})
        export = shown.assign(Time=shown["Time"].dt.strftime("%Y-%m-%d %H:%M:%S"))
        st.download_button("Download these lines (CSV)", export.to_csv(index=False).encode("utf-8"),
                           file_name=f"mpesa_{start:%Y-%m-%d}_to_{end:%Y-%m-%d}.csv", mime="text/csv",
                           icon=":material/download:", on_click="ignore")


if __name__ == "__main__":
    main()
