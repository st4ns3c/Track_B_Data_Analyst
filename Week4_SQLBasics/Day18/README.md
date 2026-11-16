# Day 18: Connecting Python to a Database

*Week 4 · SQL for Data · One function, three county/date tests, and a report the operations team can run without opening a database tool.*

Days 16 and 17 wrote SQL by hand. The operations team should not have to. Today the query lives in Python: connect to SQLite, pass the county and dates as parameters, and return a pandas DataFrame ready for the Monday report.

## The brief

Build `get_county_report(county, start_date, end_date)` that:

- connects to the SQLite sales database,
- runs a parameterized query with `?` placeholders, never string-formatted SQL,
- returns a DataFrame with `product`, `total_orders`, `total_quantity`, `total_revenue_kes`,
- is tested with at least three county and date combinations,
- handles the case where no rows are found.

The README shows example calls and the output. The pricing note explains the value of automating the weekly manual pull.

## How to run it

```bash
cd Week4_SQLBasics/Day18
python3 generate_sales_data.py
python3 report.py
```

`generate_sales_data.py` rebuilds `data/sales.db` from 28 fixed orders — a self-contained copy of the Day 16 orders data, so this folder does not depend on Day 16. `report.py` runs four examples: Mombasa, Kisumu, Nairobi, and a county with no orders. To use the function yourself:

```python
from report import get_county_report

report = get_county_report("Mombasa", "2026-08-01", "2026-09-30")
print(report.to_string(index=False))
```

## What is in this folder

| File | What it is |
|---|---|
| [`generate_sales_data.py`](generate_sales_data.py) | Creates `data/sales.db` and the `orders` table. Safe to rerun: it drops and rebuilds the table. |
| [`report.py`](report.py) | The `get_county_report()` function, date checks, a read-only connection, and the four demo calls. |
| `data/sales.db` | The generated database. Not committed; rebuild it with the generator. |

## The function

```python
get_county_report(county, start_date, end_date)
```

The SQL underneath:

```sql
SELECT product,
       COUNT(*) AS total_orders,
       SUM(quantity) AS total_quantity,
       SUM(quantity * unit_price) AS total_revenue_kes
FROM orders
WHERE LOWER(county) = LOWER(?)
  AND order_date BETWEEN ? AND ?
GROUP BY product
ORDER BY total_revenue_kes DESC, product;
```

The `?` marks are filled by `pandas.read_sql_query(..., params=(county, start, end))`. The county is case-insensitive, so `"Mombasa"` and `"mombasa"` both work.

The table has `quantity` and `unit_price`, not a stored `total_value`, so the query calculates `quantity * unit_price`. One stored price and one stored quantity cannot drift apart.

## Test 1: Mombasa, August to September

```python
report = get_county_report("Mombasa", "2026-08-01", "2026-09-30")
```

| Product | Orders | Units | Revenue (KES) |
|---|---:|---:|---:|
| Rice 25kg | 2 | 60 | 192,000 |
| Cooking Oil 5L | 2 | 100 | 85,000 |
| Sugar 1kg | 1 | 300 | 34,500 |

Mombasa ordered **KES 311,500** of stock in the period. Rice is the revenue leader even though cooking oil sold more units — the same unit-versus-value distinction from earlier in the week.

## Test 2: Kisumu, September to October

```python
report = get_county_report("Kisumu", "2026-09-01", "2026-10-31")
```

| Product | Orders | Units | Revenue (KES) |
|---|---:|---:|---:|
| Sugar 1kg | 1 | 500 | 57,500 |
| Rice 25kg | 1 | 12 | 38,400 |
| Wheat Flour 2kg | 1 | 30 | 4,800 |

Kisumu's **KES 100,700** is concentrated in one large sugar order. A manager reading only the total would miss that; the product breakdown is the useful part.

## Test 3: Nairobi, August to October

```python
report = get_county_report("Nairobi", "2026-08-01", "2026-10-31")
```

| Product | Orders | Units | Revenue (KES) |
|---|---:|---:|---:|
| Cooking Oil 5L | 1 | 35 | 29,750 |
| Maize Flour 2kg | 2 | 130 | 15,600 |
| Soap 1kg | 1 | 60 | 12,600 |

Nairobi's **KES 57,950** is spread across three products. Two maize orders carry the volume, but one cooking-oil order carries the revenue.

## No results: a county with no orders

```python
report = get_county_report("Garissa", "2026-08-01", "2026-10-31")
```

`report.empty` is `True`, and the DataFrame still has the four expected columns:

```
['product', 'total_orders', 'total_quantity', 'total_revenue_kes']
```

`report.py` prints:

```
Garissa: 2026-08-01 to 2026-10-31
  No orders found for that county and period.
```

An empty result is not an error. A county can be outside the sales area, or a week can genuinely have no orders. The function returns an empty table so the caller can decide whether to show "no orders" or treat it as a problem.

## Why the `?` placeholders matter

The unsafe version builds the SQL with an f-string:

```python
# Never do this
query = f"SELECT * FROM orders WHERE county = '{county}'"
```

If `county` is `' OR 1=1 --`, the query returns every order. Worse, a crafted value can damage the database. With a parameter, the county is data, not SQL:

```python
get_county_report("' OR 1=1 --", "2026-08-01", "2026-10-31")
```

returns **zero rows** — the string is treated as a county name that does not exist. The source is opened read-only, so a report can never write to the sales table.

The same rule applies to the dates: `params` carries all three values separately.

## Dates and error messages

- Dates use `YYYY-MM-DD` and the range is inclusive: `BETWEEN ? AND ?` includes both ends.
- `start_date` after `end_date` returns: `Start date must be on or before the end date.`
- An impossible date such as `2026-13-01` returns: `Start date must be a real date in YYYY-MM-DD format, like 2026-08-01.`
- An empty county returns: `County cannot be empty. Try 'Mombasa'.`
- A missing database or missing `orders` table says to run `generate_sales_data.py`.

The caller gets a sentence, not a traceback.

## What the operations team gets

One command instead of opening DB Browser, typing a query, changing the county, changing the dates, exporting, and pasting into Excel. The function always returns the same four columns, in the same order, so the Monday report template does not break when someone mistypes a column name.

The report is **read-only**. The source database is opened with `mode=ro`, so the weekly report cannot accidentally change or delete an order.

## Saving a copy: the `to_sql` pattern

The function returns a DataFrame. If the team wants to keep a snapshot for later queries, pandas can write it back to a separate reporting database:

```python
import sqlite3

snapshot = report.assign(
    county="Mombasa",
    period_start="2026-08-01",
    period_end="2026-09-30",
)
with sqlite3.connect("data/reports.db") as conn:
    snapshot.to_sql("county_report", conn, if_exists="replace", index=False)
```

`to_sql` creates the table on first use. `if_exists="replace"` refreshes it; `"append"` would keep a history. The reporting database is generated output, so it is ignored by git. This is the same pattern as Step 4 of today's reading; the Monday report itself only reads.

## Pricing note

**KES 15,000 for this report script** (or included in the KES 45,000 Day 16–18 setup). The manual pull takes 45 minutes a week — about **39 hours a year**, or **KES 58,500** of manager time at KES 1,500/hour — so the script pays back in about **three months** and removes the copy-paste mistakes that come with retyping a county and a date range every Monday.

## Note on the data

The data is **synthetic** and fixed: 28 orders from 3 August to 20 October 2026, with eight counties and six products. There is no randomness, so every run reproduces the same totals. Money is in Kenyan shillings.

It is a self-contained copy of the Day 16 orders data. The Day 16 folder is not read or changed. `data/sales.db` is generated output and is not committed.

## What was practised

- Connecting Python to SQLite with `sqlite3`
- Reading query results into a DataFrame with `pandas.read_sql_query`
- Passing county and date values as `?` parameters
- Grouping by product and calculating revenue from quantity and price
- Returning a clean, named DataFrame for a report
- Handling an empty result without crashing
- Validating dates and a date range
- Opening the database read-only so a report cannot change the source
- Writing a snapshot back with `to_sql` (the Step 4 pattern)
- Pricing automation against the cost of the manual routine

## Requirements

```
pip install pandas
```

Python 3.10 or later. SQLite ships with Python, so no database server is needed.
