"""
Otieno Wholesale Supplies: sales performance dashboard
------------------------------------------------------
Build plan
  Problem : the owner of a Nairobi wholesaler wants to see, without
            opening a spreadsheet, how sales are doing by county and month,
            who the biggest accounts are, and which shops have stopped
            ordering.
  Input   : data/sales_data.csv, one row per order line: order_id, date,
            customer, county, product, quantity, price.
  Output  : a Streamlit page: a short description, filters for county and
            month, four headline numbers, a revenue trend, the top ten
            accounts, and the shops that have gone quiet with the monthly
            revenue each one used to bring in.

Usage:
    streamlit run app.py

Requirements:
    pip install -r requirements.txt
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "sales_data.csv"
REQUIRED = ["order_id", "date", "customer", "county", "product", "quantity", "price"]

ACCENT = "#2a78d6"
CONTEXT = "#c3c2b7"
WARN = "#d4720f"
AVERAGE_DAYS_PER_MONTH = 30.4


class DataProblem(Exception):
    """A problem with the sales file, worded for the owner."""


@st.cache_data
def load_data():
    if not CSV_PATH.exists():
        raise DataProblem("The sales file data/sales_data.csv is missing. "
                          "Run `python generate_sales_data.py` to create it.")
    df = pd.read_csv(CSV_PATH)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DataProblem(f"The sales file is missing the column(s): {', '.join(missing)}.")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["quantity", "price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    bad = df[["date", "quantity", "price"]].isna().any(axis=1).sum()
    if bad:
        raise DataProblem(f"{bad} row(s) have a date, quantity or price that could not be read.")
    if df.empty:
        raise DataProblem("The sales file has no orders in it.")
    df["revenue"] = df["quantity"] * df["price"]
    df["month"] = df["date"].dt.to_period("M")
    return df


def kes(value):
    if abs(value) >= 1_000_000:
        return f"KES {value / 1_000_000:,.2f}M"
    return f"KES {value:,.0f}"


def headline_numbers(view):
    orders = view.groupby("order_id")["revenue"].sum()
    return {
        "revenue": view["revenue"].sum(),
        "orders": len(orders),
        "avg_order": orders.mean() if len(orders) else 0,
        "customers": view["customer"].nunique(),
    }


def trend_chart(view, by_day):
    if by_day:
        data = view.groupby("date", as_index=False)["revenue"].sum()
        x = alt.X("date:T", title="Day", axis=alt.Axis(format="%a %d"))
        mark = alt.Chart(data).mark_bar(color=ACCENT, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        tip_date = alt.Tooltip("date:T", title="Day", format="%A %d %B")
    else:
        weekly = view.assign(week=view["date"].dt.to_period("W-SUN").dt.start_time)
        data = weekly.groupby("week", as_index=False)["revenue"].sum().rename(columns={"week": "date"})
        x = alt.X("date:T", title="Week starting", axis=alt.Axis(format="%d %b"))
        mark = alt.Chart(data).mark_line(color=ACCENT, point=alt.OverlayMarkDef(size=50, color=ACCENT))
        tip_date = alt.Tooltip("date:T", title="Week starting", format="%d %B %Y")
    return mark.encode(
        x=x,
        y=alt.Y("revenue:Q", title="Revenue (KES)", axis=alt.Axis(format="~s")),
        tooltip=[tip_date, alt.Tooltip("revenue:Q", title="Revenue (KES)", format=",.0f")],
    ).properties(height=320)


def top_accounts_chart(view, n=10):
    by_customer = view.groupby("customer", as_index=False)["revenue"].sum()
    total = by_customer["revenue"].sum()
    top = by_customer.nlargest(n, "revenue")
    top["share"] = top["revenue"] / total
    top["rank"] = range(1, len(top) + 1)
    top["group"] = ["Top 3 accounts" if r <= 3 else "Next 7" for r in top["rank"]]
    bars = alt.Chart(top).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        x=alt.X("revenue:Q", title="Revenue (KES)", axis=alt.Axis(format="~s")),
        # An explicit order: "-x" is not applied once the text layer is added.
        y=alt.Y("customer:N", sort=top["customer"].tolist(), title=None),
        color=alt.Color("group:N", title=None,
                        scale=alt.Scale(domain=["Top 3 accounts", "Next 7"], range=[ACCENT, CONTEXT]),
                        legend=alt.Legend(orient="bottom")),
        tooltip=[alt.Tooltip("customer:N", title="Customer"),
                 alt.Tooltip("revenue:Q", title="Revenue (KES)", format=",.0f"),
                 alt.Tooltip("share:Q", title="Share of revenue", format=".1%")],
    )
    labels = bars.mark_text(align="left", dx=4, fontSize=11, color="#52514e").encode(
        text=alt.Text("share:Q", format=".0%"), color=alt.value("#52514e"))
    return (bars + labels).properties(height=340), top


def dormant_customers(view_all_months, as_of, quiet_days):
    """Shops whose last order is at least quiet_days before the data's last day."""
    per = view_all_months.groupby("customer").agg(
        county=("county", "first"),
        first_order=("date", "min"),
        last_order=("date", "max"),
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
    ).reset_index()
    per["days_quiet"] = (as_of - per["last_order"]).dt.days
    # What each shop used to bring in per month while it was ordering: that
    # is the revenue at risk if it does not come back.
    active_days = (per["last_order"] - per["first_order"]).dt.days.clip(lower=AVERAGE_DAYS_PER_MONTH)
    per["monthly_revenue"] = per["revenue"] / (active_days / AVERAGE_DAYS_PER_MONTH)
    quiet = per[per["days_quiet"] >= quiet_days].sort_values("monthly_revenue", ascending=False)
    return quiet


def dormant_chart(quiet):
    return alt.Chart(quiet).mark_bar(color=WARN, cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        x=alt.X("monthly_revenue:Q", title="Revenue it used to bring in each month (KES)",
                axis=alt.Axis(format="~s")),
        y=alt.Y("customer:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("customer:N", title="Customer"),
                 alt.Tooltip("county:N", title="County"),
                 alt.Tooltip("last_order:T", title="Last order", format="%a %d %b %Y"),
                 alt.Tooltip("days_quiet:Q", title="Days since last order"),
                 alt.Tooltip("monthly_revenue:Q", title="Monthly revenue before (KES)", format=",.0f")],
    ).properties(height=max(120, 30 * len(quiet)))


def main():
    st.set_page_config(page_title="Otieno Wholesale Sales", page_icon="📦", layout="wide")

    try:
        df = load_data()
    except DataProblem as problem:
        st.error(str(problem))
        st.stop()

    as_of = df["date"].max()
    st.title("Sales Performance Dashboard: Otieno Wholesale Supplies")
    st.markdown(
        "Track sales by county and month, see your biggest accounts, and find the shops that "
        "have stopped ordering. Use the filters on the left to look at one county or one month. "
        f"**Data up to {as_of:%A %d %B %Y}.**"
    )

    with st.sidebar:
        st.header("Filters")
        counties = ["All counties"] + sorted(df["county"].unique())
        county = st.selectbox("County", counties)
        months = sorted(df["month"].unique(), reverse=True)
        month_labels = {f"{m:%B %Y}": m for m in months}
        month_choice = st.selectbox("Month", ["All months"] + list(month_labels))
        quiet_days = st.select_slider("Treat a shop as quiet after (days without an order)",
                                      options=[14, 21, 30, 45, 60, 90], value=30)
        st.caption("Sample data for a fictional business.")

    by_county = df if county == "All counties" else df[df["county"] == county]
    month = month_labels.get(month_choice)
    view = by_county if month is None else by_county[by_county["month"] == month]
    if view.empty:
        st.warning(f"No orders for {county} in {month_choice}. Try another county or month.")
        st.stop()

    partial = month is not None and month == as_of.to_period("M") and as_of.day < month.days_in_month
    nums = headline_numbers(view)
    deltas = {}
    if month is not None and not partial:
        previous = by_county[by_county["month"] == month - 1]
        if not previous.empty:
            before = headline_numbers(previous)
            deltas = {k: (nums[k] - before[k]) / before[k] for k in nums if before[k]}

    k1, k2, k3, k4 = st.columns(4)
    def delta(k):
        """Delta text and colour; a change under half a percent shows as grey 'no change'."""
        if k not in deltas:
            return {"delta": None}
        if abs(deltas[k]) < 0.005:
            return {"delta": f"No change on {month - 1:%B}", "delta_color": "off", "delta_arrow": "off"}
        return {"delta": f"{deltas[k]:+.0%} on {month - 1:%B}"}

    k1.metric("Total revenue", kes(nums["revenue"]), border=True, **delta("revenue"))
    k2.metric("Orders", f"{nums['orders']:,}", border=True, **delta("orders"))
    k3.metric("Average order", kes(nums["avg_order"]), border=True, **delta("avg_order"))
    k4.metric("Customers who ordered", f"{nums['customers']}", border=True, **delta("customers"))
    if partial:
        st.caption(f"{month_choice} is month to date (up to {as_of:%d %B}), so there is no "
                   "comparison with last month yet.")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Revenue trend")
        st.altair_chart(trend_chart(view, by_day=month is not None), width="stretch")
        if month is None:
            st.caption(f"Weekly revenue. The last week runs to {as_of:%d %B}, so it may be short.")
    with right:
        st.subheader("Top 10 accounts")
        chart, top = top_accounts_chart(view)
        st.altair_chart(chart, width="stretch")
        where = (county.lower() if county == "All counties" else county) + (
            "" if month is None else f" in {month_choice}")
        if len(top) > 3:
            st.caption(f"The top 3 bring in {top['share'].head(3).sum():.0%} of revenue for {where}.")
        else:
            st.caption(f"Only {len(top)} shop{'s' if len(top) != 1 else ''} ordered for {where}.")

    st.subheader("Shops that have stopped ordering")
    quiet = dormant_customers(by_county, as_of, quiet_days)
    if quiet.empty:
        st.success(f"Every shop{'' if county == 'All counties' else ' in ' + county} has ordered "
                   f"in the last {quiet_days} days.")
    else:
        at_risk = quiet["monthly_revenue"].sum()
        st.markdown(
            f"**{len(quiet)} shop{'s' if len(quiet) != 1 else ''}** "
            f"{'have' if len(quiet) != 1 else 'has'} not ordered for {quiet_days} days or more. "
            f"Together they used to bring in about **{kes(at_risk)} a month**. "
            "A call this week is the cheapest sale you will make."
        )
        st.altair_chart(dormant_chart(quiet), width="stretch")
        st.caption(f"Counted up to {as_of:%d %B %Y}, across all months, so the month filter does not "
                   "change this list. Hover over a bar for the last order date.")
        call_list = quiet[["customer", "county", "last_order", "days_quiet", "monthly_revenue"]].rename(
            columns={"customer": "Customer", "county": "County", "last_order": "Last order",
                     "days_quiet": "Days quiet", "monthly_revenue": "Monthly revenue before (KES)"})
        call_list["Last order"] = call_list["Last order"].dt.strftime("%Y-%m-%d")
        call_list["Monthly revenue before (KES)"] = call_list["Monthly revenue before (KES)"].round(0)
        st.download_button("Download the call list (CSV)", call_list.to_csv(index=False).encode("utf-8"),
                           file_name=f"quiet_shops_{as_of:%Y-%m-%d}.csv", mime="text/csv",
                           icon=":material/download:", on_click="ignore")

    with st.expander("See the orders behind these numbers"):
        shown = view.sort_values("date", ascending=False).copy()
        shown["date"] = shown["date"].dt.strftime("%a %d %b %Y")
        st.dataframe(shown.drop(columns=["month"]), hide_index=True, width="stretch",
                     column_config={"price": st.column_config.NumberColumn("Price (KES)", format="%,d"),
                                    "revenue": st.column_config.NumberColumn("Revenue (KES)", format="%,d")})


if __name__ == "__main__":
    main()
