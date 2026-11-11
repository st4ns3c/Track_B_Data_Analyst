# Day 15: Project, Complex Analysis

*Week 3 · Advanced Data Analysis · Last day of the week. One project, one exercise, both published.*

Day 15 is the week's consolidation: take the four days of advanced pandas and build one complete analysis, with charts that answer specific questions and conclusions written in plain language. This folder holds two independent pieces, each with its own scripts, data and README.

## What is here

| Folder | What it is | Question it answers |
|---|---|---|
| [`project/`](project/README.md) | **The project.** A distributor's order data for August and September, across Nairobi and Mombasa | How did the two months compare, which region carries the business, and which customers matter? |
| [`exercise/`](exercise/README.md) | **The exercise, Option 1.** Daily vegetable prices at a Nairobi market, May to October 2026 | Which of five vegetables has the most volatile price, when does it peak, and why? |

Both are self-contained. Each has its own `generate_sample_data.py`, its own `data/` folder, its own analysis script, its own chart and its own README explaining the method and the finding.

## The project in one paragraph

Revenue fell **11.0%** from August (KES 1,066,325) to September (KES 948,600). The fall is not broad: **Nairobi grew 11.9%** while **Mombasa fell 58.9%**, and the three biggest customers grew about **35%** to supply **68%** of September revenue while every other account combined fell **48.6%**. Six Mombasa customers went quiet, taking **KES 85,770** of August revenue with them. Four charts, each answering one question, and a four-sentence findings summary.

```bash
cd project
python generate_sample_data.py && python analysis.py
```

## The exercise in one paragraph

Of five vegetables tracked daily for six months, **tomatoes are by far the most volatile** — a coefficient of variation of **18.4%**, with the 7-day average peaking at **KES 142/kg on 10 September 2026**. **Onions are the steadiest at 5.0%**. Kale and cabbage tie at 8.8%, potatoes sit at 7.1%. Measuring with CV rather than standard deviation is the point: onions have a bigger standard deviation than kale purely because they cost three times as much.

```bash
cd exercise
python generate_sample_data.py && python analysis.py
```

Why Option 1: the volatility question needs a rolling average, a normalised spread measure and a per-series panel chart, which is a better fit for this week's time-series and statistics work than repeating a merge exercise.

## What each piece demonstrates

| Technique | Project | Exercise |
|---|---|---|
| Two files with different schemas | `client_name`/`county`/`qty`/`unit_price` vs `customer_name`/`region`/`quantity`/`price` | — |
| Cleaning inconsistent names | `kamau stores`, `KAMAU STORES `, `Kamau  Stores` → one customer | — |
| Time series | Month-over-month comparison | Daily prices, 7-day rolling average, monthly resample |
| Statistics | Tier thresholds, share of revenue, percentage change | Coefficient of variation, standard deviation, mean |
| Aggregation | `groupby`, `pivot_table`, `size` | `pivot`, `rolling`, `resample` |
| Charts | Four panels, one question each | Five panels, one time series each, peaks annotated |
| Defensive input checks | Dates, numerics, zero prices, duplicate rows | Dates, numerics, zero prices, duplicate days |

## What the week covered, and where it shows up

| Day | Topic | Where it appears in Day 15 |
|---|---|---|
| 11 | Advanced pandas: merge, pivot, apply | Both: pivot tables and grouped aggregation |
| 12 | Time series: dates, resampling, trend | Exercise: daily series, 7-day average, monthly averages |
| 13 | Statistics: spread, outliers | Exercise: CV and the standard deviation trap |
| 14 | Multi-dataset: clean, join, correlate | Project: two exports with mismatched columns and names |
| 15 | One complete analysis | Both, end to end |

## Note on the data

Both datasets are **synthetic**, written by their generators with fixed seeds (15) so every run reproduces the same numbers. The mess in the project data — mismatched column names, differently typed customer names — and the seasonal shapes in the exercise are built in on purpose, to make the cleaning and the analysis the actual work.

## Requirements

```
pip install pandas numpy matplotlib
```

Python 3.10 or later. Charts are written with the `Agg` backend, so no display is needed.
