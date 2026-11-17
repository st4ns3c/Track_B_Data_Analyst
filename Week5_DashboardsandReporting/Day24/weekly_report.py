"""
Nutrition programme: the Monday morning report
----------------------------------------------
Build plan
  Problem : the NGO's programme director wants a report every Monday
            morning without asking for it: one HTML file she can open,
            print or forward, dated so she knows it is current.
  Input   : data/nutrition_outcomes.csv (the Day 23 programme data;
            rebuild with generate_nutrition_data.py).
  Output  : charts/*.png, the three finding charts, redrawn each run.
            reports/report_YYYY-MM-DD.html, one self-contained file: the
            date in the title, a one-paragraph summary, four headline
            numbers, and the three charts embedded inside the file, so it
            opens anywhere with no other files beside it.
            logs/report.log, one line per run.

The findings and charts come from story_analysis.py (copied from Day 23),
so the report and the donor brief always tell the same story.

Usage:
    python weekly_report.py                    # report dated today
    python weekly_report.py --date 2026-11-23  # report dated a given day

Running twice on the same day replaces that day's file; each new day gets
its own file. schedule_reports.py runs this every Monday at 07:00.

Requirements:
    pip install pandas numpy matplotlib
"""

import argparse
import base64
import html
import logging
import sys
from datetime import date, datetime
from pathlib import Path

import story_analysis as sa

BASE_DIR = Path(__file__).parent
REPORT_DIR = BASE_DIR / "reports"
LOG_PATH = BASE_DIR / "logs" / "report.log"
# Weekly data that is more than this many days old gets a visible warning.
STALE_AFTER_DAYS = 8


class ReportError(Exception):
    """A problem worded for the programme director, not a traceback."""


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
    )


def load_data():
    try:
        return sa.load()
    except sa.DataProblem as problem:
        raise ReportError(str(problem))


def embed_png(path):
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def summary_paragraph(df, f1, f2, f3):
    c, g = f1["table"], f3["table"]
    best, worst, young = f1["best"], f1["worst"], f3["fastest"]
    attendance = df["sessions_attended"].sum() / df["sessions_offered"].sum()
    text = (
        f"The programme is reaching {len(df)} children in "
        f"{', '.join(sorted(df['county'].unique()))}. Together they have gained "
        f"{df['weight_gain_kg'].sum():,.0f} kg, an average of "
        f"{sa.per_month(df):.2f} kg per child per month, and families attended "
        f"{attendance:.0%} of sessions. {best} is doing best "
        f"({c.loc[best, 'kg_per_month']:.2f} kg a month) and {worst} is behind "
        f"({c.loc[worst, 'kg_per_month']:.2f} kg)"
    )
    if f1["explained"]:
        text += (f", mostly because {worst} families come to fewer sessions "
                 f"({c.loc[worst, 'attendance']:.0%} against {c.loc[best, 'attendance']:.0%})")
    text += (
        f". Children who attend 90% or more of sessions gain "
        f"{f2['high']:.2f} kg a month, against {f2['low']:.2f} kg for those who come to "
        f"fewer than half. Children aged {young} are gaining fastest, at "
        f"{g.loc[young, 'kg_per_month']:.2f} kg a month."
    )
    return text


def freshness(report_day):
    modified = datetime.fromtimestamp(sa.CSV_PATH.stat().st_mtime)
    age = (report_day - modified.date()).days
    note = None
    if age > STALE_AFTER_DAYS:
        note = (f"The data file was last updated {age} days before this report, so these "
                "figures may be the same as last week's. Please check that this week's "
                "records were added.")
    return modified, note


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
           --line: #e1e0d9; --surface: #fcfcfb; --page: #f9f9f7; --accent: #2a78d6;
           --warn-bg: #fff4d6; --warn-ink: #5c4300; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--page); color: var(--ink);
          font: 16px/1.55 "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 48px; background: var(--surface); }}
  h1 {{ font-size: 1.7rem; line-height: 1.25; margin: 0 0 4px; }}
  .dateline {{ color: var(--ink-2); margin: 0 0 24px; }}
  .summary {{ font-size: 1.05rem; margin: 0 0 24px; }}
  .tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 0 0 32px; }}
  .tile {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }}
  .tile .label {{ color: var(--ink-2); font-size: .85rem; }}
  .tile .value {{ font-size: 1.5rem; font-weight: 600; }}
  .warning {{ background: var(--warn-bg); color: var(--warn-ink); border-radius: 8px;
              padding: 12px 16px; margin: 0 0 24px; }}
  section {{ margin: 0 0 32px; break-inside: avoid; }}
  section h2 {{ font-size: .8rem; letter-spacing: .06em; text-transform: uppercase;
                color: var(--ink-2); margin: 0 0 8px; }}
  section img {{ width: 100%; height: auto; border: 1px solid var(--line); border-radius: 8px; }}
  footer {{ border-top: 1px solid var(--line); padding-top: 12px; color: var(--muted); font-size: .85rem; }}
  @media (max-width: 640px) {{ .tiles {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media print {{
    body {{ background: #fff; }}
    main {{ padding: 0; max-width: none; }}
    section {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="dateline">Child nutrition programme · {counties}</p>
  {warning}
  <p class="summary">{summary}</p>
  <div class="tiles">
    {tiles}
  </div>
  {sections}
  <footer>
    Report generated {generated}. Data file last updated {data_updated}
    ({data_name}, {rows} children). Figures are weight gained per month in the programme,
    because children joined at different times. Synthetic data for this exercise.
  </footer>
</main>
</body>
</html>
"""


def build_report(report_day=None):
    report_day = report_day or date.today()
    df = load_data()
    sa.CHART_DIR.mkdir(exist_ok=True)

    f1, f2, f3 = sa.county_finding(df), sa.attendance_finding(df), sa.age_finding(df)
    charts = [
        (f1["headline"], sa.chart_county(f1["table"], f1["headline"], f1["best"])),
        (f2["headline"], sa.chart_attendance(f2["table"], f2["headline"])),
        (f3["headline"], sa.chart_age(f3["table"], f3["headline"], f3["fastest"])),
    ]

    attendance = df["sessions_attended"].sum() / df["sessions_offered"].sum()
    tiles = [
        ("Children in the programme", f"{len(df):,}"),
        ("Weight gained in total", f"{df['weight_gain_kg'].sum():,.0f} kg"),
        ("Gain per child per month", f"{sa.per_month(df):.2f} kg"),
        ("Sessions attended", f"{attendance:.0%}"),
    ]
    modified, stale_note = freshness(report_day)

    title = f"Nutrition Programme Report: {report_day:%A %d %B %Y}"
    page = PAGE.format(
        title=html.escape(title),
        counties=html.escape(", ".join(sorted(df["county"].unique()))),
        warning=f'<p class="warning">{html.escape(stale_note)}</p>' if stale_note else "",
        summary=html.escape(summary_paragraph(df, f1, f2, f3)),
        tiles="\n    ".join(
            f'<div class="tile"><div class="label">{html.escape(label)}</div>'
            f'<div class="value">{html.escape(value)}</div></div>'
            for label, value in tiles
        ),
        sections="\n  ".join(
            # The headline is already the chart's title, so the heading is a
            # short label; the alt text carries the headline for screen readers.
            f'<section><h2>Finding {n} of {len(charts)}</h2>'
            f'<img src="{embed_png(path)}" alt="{html.escape(headline)}"></section>'
            for n, (headline, path) in enumerate(charts, 1)
        ),
        generated=f"{datetime.now():%A %d %B %Y at %H:%M}",
        data_updated=f"{modified:%A %d %B %Y at %H:%M}",
        data_name=html.escape(sa.CSV_PATH.name),
        rows=len(df),
    )

    REPORT_DIR.mkdir(exist_ok=True)
    out = REPORT_DIR / f"report_{report_day:%Y-%m-%d}.html"
    replaced = out.exists()
    out.write_text(page, encoding="utf-8")
    logging.info(f"{'Replaced' if replaced else 'Saved'} {out.relative_to(BASE_DIR)} "
                 f"({out.stat().st_size / 1024:.0f} KB, {len(df)} children)"
                 + (" - data looks stale" if stale_note else ""))
    return out


def parse_args():
    parser = argparse.ArgumentParser(description="Build the dated nutrition programme report.")
    parser.add_argument("--date", help="report date as YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    if args.date:
        try:
            args.date = date.fromisoformat(args.date)
        except ValueError:
            parser.error(f"'{args.date}' is not a date. Use YYYY-MM-DD, for example 2026-11-23.")
    return args


def main():
    setup_logging()
    args = parse_args()
    try:
        out = build_report(args.date)
    except ReportError as problem:
        logging.error(f"Report not built: {problem}")
        sys.exit(1)
    print(f"Open it in a browser: {out}")


if __name__ == "__main__":
    main()
