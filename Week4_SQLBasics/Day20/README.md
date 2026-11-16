# Day 20: Project, Database Analysis

*Week 4 · SQL for Data · Last day of the week. One project, one exercise, both published.*

Four days of SQL, then one complete database analysis. Python builds a SQLite database, SQL gets the data, pandas shapes the insight, matplotlib draws it, and a written report turns it into something a client can act on. This folder holds two independent pieces, each with its own generator, database, analysis script, chart, report and README.

## What is here

| Folder | What it is | Questions it answers |
|---|---|---|
| [`project/`](project/README.md) | **The project.** Baraka Distributors, Q1 2024: 194 orders, five products, five counties | Which products drive revenue? Where is revenue concentrated? Is every county growing? |
| [`exercise/`](exercise/README.md) | **The exercise.** A Kisumu fish market's first three months of digital sales, for a county government sponsor | Top three vendors? Wholesale or retail per kg? Revenue up, flat or down? |

## The project in one paragraph

**Rice and Maize Flour bring in 66%** of Baraka's KES 54.1M quarter, and **Nairobi and Kisumu carry 67%** of sales. **Mombasa has 4.9%**, and its revenue fell 39% from January to March while the business grew 26%. Mombasa's orders are normal-sized; there are just nine of them, so the recommendation is a dedicated sales contact to win more shops. Matching Eldoret, the smallest established county, is worth about **KES 4.1M a quarter**. Report: [`project/findings_report.md`](project/findings_report.md).

```bash
cd project
python generate_baraka_data.py && python analysis.py
```

## The exercise in one paragraph

**Otieno & Sons, Akinyi Fish Stall and Awino Fresh Fish** earn 58% of the market's KES 1.78M. **Retail earns more per kg** (KES 324 against 254; 11% to 22% more within each fish type), but **wholesale brings in 60% of revenue** because its sales are four times larger. **Revenue is trending up**: the weekly trend line rises 79% over the quarter. Recommendation: link the five smaller vendors to wholesale buyers. Report: [`exercise/report.md`](exercise/report.md), with the pricing note in the [exercise README](exercise/README.md#pricing-note).

```bash
cd exercise
python generate_fish_market_data.py && python analysis.py
```

## What each piece demonstrates

| Technique | Project | Exercise |
|---|---|---|
| Building the database from Python | Lesson's `sales` table, `CHECK` constraints, two indexes | Six-field `sales` table, `CHECK` on buyer type, date index |
| Aggregation | Revenue, units, orders, average order value | Revenue by vendor, kg-weighted revenue per kg |
| Conditional aggregation | — | Retail and wholesale side by side per fish type |
| Window functions | `LAG` for month-on-month change | `LAG` for month-on-month change |
| Date handling | `strftime('%Y-%m')` months | Monday-start weeks with `date(..., 'weekday 0', '-6 days')` |
| pandas layer | Shares, cumulative share, county × month pivot, benchmark gap | Shares, retail premium, trend fit with `numpy.polyfit` |
| Chart | Three panels, problem county in red | One chart: weekly bars and trend line |
| Report | `findings_report.md`, generated from the queries | `report.md`, ~200 words, generated from the queries |
| Safety | Read-only connection, plain-language errors | Read-only connection, plain-language errors |

## What the week covered, and where it shows up

| Day | Topic | Where it appears in Day 20 |
|---|---|---|
| 16 | SQL basics: `SELECT`, `WHERE`, `ORDER BY`, aggregates | Both: every query |
| 17 | Joins and subqueries | Both use one table by design; CTEs carry the multi-step logic |
| 18 | Connecting Python to a database | Both: `sqlite3` to build, `pd.read_sql_query` to read, read-only URI |
| 19 | Analytical queries: `LAG`, `CASE WHEN`, indexes | Both: `LAG`, conditional aggregation, indexes matched to the queries |
| 20 | One complete analysis | Both, end to end |

## Note on the data

Both datasets are **synthetic**, written by generators with fixed seeds (2024 for the project, 20 for the exercise), so every run reproduces the same numbers. The databases are generated output and are not committed; run the generator first. The reports and charts are committed, because they are the deliverables.

## Requirements

```
pip install pandas numpy matplotlib
```

Python 3.10 or later. SQLite ships with Python. Charts use the `Agg` backend, so no display is needed.
