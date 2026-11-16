# Day 19: Writing Analytical Queries

*Week 4 · SQL for Data · Three board questions answered in SQL, then checked against the query plan.*

The first three days of the week produced totals. The CFO does not need another total; she needs trends. Today's queries answer the questions that came up in the last board meeting: where orders stall, which customers are actually growing, and how revenue accumulates through the quarter.

## The brief

Using the orders and customers database, write SQL to answer:

1. For each county, what percentage of orders were completed, pending or cancelled?
2. Which customers increased their order value month on month for at least two consecutive months? Use `LAG`.
3. What is the running total of revenue by date across all counties?

Run each query with pandas, print a clean result, and write one business interpretation sentence per query as a code comment. The README carries the three sentences as they would appear in a board report.

## How to run it

```bash
cd Week4_SQLBasics/Day19
python3 generate_analytical_data.py
python3 analytics.py
```

`generate_analytical_data.py` rebuilds `data/analytics.db`, prints the order counts and the query plan before and after indexing, and leaves the database ready for the report. `analytics.py` opens it read-only, runs the three queries plus a `HAVING` bonus, and confirms the county index is used.

## What is in this folder

| File | What it is |
|---|---|
| [`generate_analytical_data.py`](generate_analytical_data.py) | Creates `data/analytics.db`, both tables, the 41 fixed orders and the two indexes. Shows `SCAN` before and `SEARCH` after. |
| [`analytics.py`](analytics.py) | The three analytical queries, the `HAVING` bonus and the query-plan check, all through `pandas.read_sql_query`. |
| `data/analytics.db` | The generated database. Not committed; rebuild it with the generator. |

## The data

| `customers` | `orders` |
|---|---|
| 12 customers | 41 orders |
| `customer_id`, `customer_name`, `county`, `account_tier` | `order_id`, `customer_id`, `product`, `quantity`, `unit_price`, `order_date`, `status` |

Orders run from **3 August to 28 October 2026**: 27 completed, 9 pending and 5 cancelled. Completed means delivered and paid. Pending is still expected business. **Revenue in queries 2 and 3 excludes cancelled orders**, because a cancelled order is not revenue; query 1 deliberately includes all three statuses, because the status mix is the point. Cancelled rows sit beside a live order in the same customer-month, so removing them never hides a whole month from the trend.

Non-cancelled revenue: **KES 1,569,550** across 36 order dates.

## From question to query

Every query below started as a sentence:

| Business question | SQL technique |
|---|---|
| "Where do orders stall by county?" | `GROUP BY` county, conditional `SUM(CASE WHEN ...)` for each status, percentages |
| "Who is growing two months in a row?" | Monthly totals per customer, then `LAG` to compare with the previous month |
| "How fast is revenue accumulating?" | Daily totals, then `SUM(...) OVER (ORDER BY date)` |
| "Which counties break a cancellation threshold?" | `HAVING` on the aggregated cancellation share |

`WHERE` filters rows **before** grouping. `HAVING` filters groups **after** aggregation, which is why a condition on `COUNT`, `SUM` or `AVG` belongs in `HAVING`.

Both queries name their columns. `SELECT *` is fine while exploring, but a report that pulls 30 columns to use four wastes time and breaks when a column is renamed.

## Query 1: order status mix by county

```sql
SELECT c.county,
       COUNT(*) AS total_orders,
       SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) AS completed,
       SUM(CASE WHEN o.status = 'pending'   THEN 1 ELSE 0 END) AS pending,
       SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS completed_pct,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS pending_pct,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS cancelled_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.county
ORDER BY cancelled_pct DESC, c.county;
```

| County | Orders | Completed | Pending | Cancelled | Completed % | Pending % | Cancelled % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Machakos | 4 | 2 | 1 | 1 | 50.0 | 25.0 | 25.0 |
| Mombasa | 4 | 2 | 1 | 1 | 50.0 | 25.0 | 25.0 |
| Eldoret | 7 | 5 | 1 | 1 | 71.4 | 14.3 | 14.3 |
| Kisumu | 9 | 6 | 2 | 1 | 66.7 | 22.2 | 11.1 |
| Nairobi | 10 | 7 | 2 | 1 | 70.0 | 20.0 | 10.0 |
| Nakuru | 3 | 2 | 1 | 0 | 66.7 | 33.3 | 0.0 |
| Nyeri | 3 | 3 | 0 | 0 | 100.0 | 0.0 | 0.0 |
| Thika | 1 | 0 | 1 | 0 | 0.0 | 100.0 | 0.0 |

**Board interpretation:** Every county completes at least half of its orders, but Mombasa and Machakos cancel one order in four — double the network average of 12.2% — so fulfilment is a regional problem rather than a company-wide one.

The conditional `SUM(CASE WHEN status = ... THEN 1 ELSE 0 END)` counts each status inside one pass. A plain `GROUP BY status` would need a second pivot step in pandas, and the board table would arrive as 24 rows instead of eight.

Two rows need context before anyone panics. Thika's 100% pending is a single order from a customer with no earlier orders. Nyeri's 100% completion is three orders, all completed. A percentage on a tiny base is noisy; the `Orders` column is there so nobody reads "100%" as "perfect county".

## Query 2: customers growing two months in a row

```sql
WITH monthly AS (
    SELECT c.customer_id,
           c.customer_name,
           c.county,
           strftime('%Y-%m', o.order_date) AS month,
           CAST(strftime('%Y', o.order_date) AS INTEGER) * 12
             + CAST(strftime('%m', o.order_date) AS INTEGER) AS month_no,
           SUM(o.quantity * o.unit_price) AS month_value
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id, c.customer_name, c.county, month, month_no
),
compared AS (
    SELECT customer_id, customer_name, county, month, month_no, month_value,
           LAG(month_value) OVER w AS previous_value,
           LAG(month) OVER w AS previous_month,
           LAG(month_no) OVER w AS previous_month_no
    FROM monthly
    WINDOW w AS (PARTITION BY customer_id ORDER BY month_no)
),
flagged AS (
    SELECT customer_id, customer_name, county, month, month_value,
           previous_value, previous_month,
           CASE WHEN previous_value IS NOT NULL
                     AND month_no - previous_month_no = 1
                     AND month_value > previous_value
                THEN 1 ELSE 0 END AS increased
    FROM compared
),
streaks AS (
    SELECT *,
           LAG(increased) OVER (
               PARTITION BY customer_id ORDER BY month
           ) AS previous_increased
    FROM flagged
),
qualifying AS (
    SELECT DISTINCT customer_id
    FROM streaks
    WHERE increased = 1 AND previous_increased = 1
)
SELECT customer_name,
       county,
       month,
       previous_month,
       previous_value,
       month_value,
       month_value - previous_value AS growth_value,
       ROUND(100.0 * (month_value - previous_value) / previous_value, 1)
         AS growth_pct
FROM streaks
WHERE increased = 1
  AND customer_id IN (SELECT customer_id FROM qualifying)
ORDER BY customer_name, month;
```

| Customer | County | Month | Previous month | Previous (KES) | Month (KES) | Growth (KES) | Growth % |
|---|---|---|---|---:|---:|---:|---:|
| Kamau Stores | Nairobi | 2026-09 | 2026-08 | 23,000 | 28,450 | 5,450 | 23.7 |
| Kamau Stores | Nairobi | 2026-10 | 2026-09 | 28,450 | 35,100 | 6,650 | 23.4 |
| Njeri Enterprises | Nyeri | 2026-09 | 2026-08 | 9,600 | 23,800 | 14,200 | 147.9 |
| Njeri Enterprises | Nyeri | 2026-10 | 2026-09 | 23,800 | 29,750 | 5,950 | 25.0 |

**Board interpretation:** Only Kamau Stores and Njeri Enterprises have grown for two consecutive months, and both are modest accounts, so the growth story is coming from customers the board has not been watching.

For context, every customer's monthly value:

| Customer | Aug (KES) | Sep (KES) | Oct (KES) | Pattern |
|---|---:|---:|---:|---|
| Kamau Stores | 23,000 | 28,450 | 35,100 | **up, up** |
| Njeri Enterprises | 9,600 | 23,800 | 29,750 | **up, up** |
| Otieno Wholesale | 80,000 | 96,000 | 64,000 | up, down |
| Hassan Traders | 128,000 | 112,000 | 144,000 | down, up |
| Kiprono Stores | 48,000 | 32,000 | 38,400 | down, up |
| Ochieng Supplies | 46,000 | 34,500 | 57,500 | down, up |
| Waweru Ltd | 12,000 | 20,700 | 17,250 | up, down |
| Njoroge Supplies | 22,400 | 34,500 | 23,000 | up, down |
| Mutua Wholesale | 96,000 | 29,750 | 144,000 | down, up |
| Chebet Distributors | 46,000 | 28,750 | 34,500 | down, up |
| Achieng Retail | — | 12,600 | 9,600 | down |
| Mwangi Mini Mart | — | — | 8,400 | one month |

`LAG(month_value)` pulls the previous month's value onto the current row, so a row can be compared without a self-join. `PARTITION BY customer_id` restarts the comparison for each customer; without it, the first Kamau row would be compared with Mwangi's last month.

Two details make the streak test honest:

- **The month gap check.** `month_no - previous_month_no = 1` ensures the previous row really is the previous calendar month. Without it, a customer who ordered in August and October would look like a one-month increase across a missing September.
- **The second `LAG`.** `LAG(increased)` asks whether the previous month was also an increase. Requiring both flags is the SQL way of saying "two in a row" without hard-coding September and October.

The `qualifying` CTE then returns every increase for those customers, not just the second one, so the board sees the full streak rather than a single row that claims one.

## Query 3: running revenue by date

```sql
WITH daily AS (
    SELECT order_date,
           SUM(quantity * unit_price) AS daily_revenue
    FROM orders
    WHERE status <> 'cancelled'
    GROUP BY order_date
)
SELECT order_date,
       daily_revenue,
       SUM(daily_revenue) OVER (
           ORDER BY order_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_total
FROM daily
ORDER BY order_date;
```

36 order dates. The first ten:

| Date | Daily revenue (KES) | Running total (KES) |
|---|---:|---:|
| 2026-08-03 | 6,000 | 6,000 |
| 2026-08-05 | 80,000 | 86,000 |
| 2026-08-07 | 128,000 | 214,000 |
| 2026-08-10 | 12,000 | 226,000 |
| 2026-08-11 | 22,400 | 248,400 |
| 2026-08-12 | 17,000 | 265,400 |
| 2026-08-14 | 48,000 | 313,400 |
| 2026-08-17 | 96,000 | 409,400 |
| 2026-08-18 | 46,000 | 455,400 |
| 2026-08-20 | 9,600 | 465,000 |

The last six:

| Date | Daily revenue (KES) | Running total (KES) |
|---|---:|---:|
| 2026-10-16 | 34,500 | 1,320,300 |
| 2026-10-18 | 144,000 | 1,464,300 |
| 2026-10-20 | 57,500 | 1,521,800 |
| 2026-10-21 | 29,750 | 1,551,550 |
| 2026-10-22 | 9,600 | 1,561,150 |
| 2026-10-26 | 8,400 | 1,569,550 |

Month-end checkpoints:

| Date | Running total (KES) |
|---|---:|
| 2026-08-21 | 511,000 |
| 2026-09-28 | 964,050 |
| 2026-10-26 | 1,569,550 |

`analytics.py` prints all 36 rows; the tables above show the start, the finish and the month ends.

**Board interpretation:** Revenue passed KES 1 million on 8 October and closed the quarter at KES 1,569,550, but two bulk rice orders in October added KES 288,000 between them, so growth is lumpy rather than steady.

`SUM(...) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` adds every earlier day to the current one. The `daily` CTE first collapses multiple orders on the same date, so the running total counts each day once. `ROWS BETWEEN ...` is explicit: without a frame, SQLite's default can include peers or behave differently from what a reader expects.

The running total is where a trend line becomes visible. August built to KES 511,000 over 11 order dates; September added KES 453,050, and October added KES 605,500 in 13 dates. The two KES 144,000 rice orders on 9 and 18 October are visible as near-vertical steps, which is exactly the shape a board should see before someone promises "steady growth".

## Bonus: `HAVING` a threshold

```sql
SELECT c.county,
       COUNT(*) AS total_orders,
       SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS cancelled_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.county
HAVING 1.0 * SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)
       / COUNT(*) > 0.10
ORDER BY cancelled_pct DESC, c.county;
```

| County | Orders | Cancelled | Cancelled % |
|---|---:|---:|---:|
| Machakos | 4 | 1 | 25.0 |
| Mombasa | 4 | 1 | 25.0 |
| Eldoret | 7 | 1 | 14.3 |
| Kisumu | 9 | 1 | 11.1 |

A board does not need the full status table every month; it needs the exceptions. `HAVING` compares the exact fraction, not the rounded percentage, so a county at 10.1% still appears even though it would round to 10.0.

## Reading the query plan

SQLite can show how it intends to run a query:

```sql
EXPLAIN QUERY PLAN
SELECT customer_id, customer_name FROM customers WHERE county = 'Mombasa';
```

Before indexing, the generator prints:

```
SCAN customers
```

Every customer row is read. After the index:

```
SEARCH customers USING INDEX idx_customers_county (county=?)
```

SQLite jumps straight to the Mombasa rows. The generator also adds `idx_orders_customer` on `orders(customer_id)`, the join key every report uses, since an unindexed foreign key forces a scan of the child table for each customer.

`analytics.py` re-runs the plan check through the read-only connection and prints `SEARCH customers USING INDEX idx_customers_county (county=?)`, so the report proves the optimisation survived the rebuild.

On 41 rows this makes no measurable difference; on a million rows it is the difference between a report and a coffee break. The index is created by the generator, not the report, because the report must never write to the database.

## What the board should take away

> Every county completes at least half of its orders, but Mombasa and Machakos cancel one order in four — double the network average of 12.2% — so fulfilment is a regional problem rather than a company-wide one.
>
> Only Kamau Stores and Njeri Enterprises have grown for two consecutive months, and both are modest accounts, so the growth story is coming from customers the board has not been watching.
>
> Revenue passed KES 1 million on 8 October and closed the quarter at KES 1,569,550, but two bulk rice orders in October added KES 288,000 between them, so growth is lumpy rather than steady.

## Pricing note

**KES 12,000 for the analytical pack, or KES 55,000 across the Day 16–19 reporting setup.** Before this, the three board answers meant exporting to Excel, building pivot tables and ranking by hand — roughly **five hours a quarter, about 20 hours a year, or KES 30,000** of analyst time at KES 1,500/hour. The pack pays back in under five months and removes the two-day wait that made the questions awkward to ask.

## Note on the data

The data is **synthetic** and fixed: 12 customers and 41 orders from 3 August to 28 October 2026. Statuses are 27 completed, 9 pending and 5 cancelled. There is no randomness, so every run reproduces the same percentages, monthly values and running total. Money is in Kenyan shillings.

The cancelled rows were placed beside a live order in the same customer-month, so excluding them from revenue cannot erase a month from the `LAG` comparison. `data/analytics.db` is generated output and is not committed.

## What was practised

- Turning three board questions into SQL before writing code
- Conditional aggregation to build a status table in one pass
- `HAVING` to filter groups after aggregation
- Window functions: `LAG` for month-on-month comparison and `SUM(...) OVER` for a running total
- `PARTITION BY` to restart a window per customer
- A calendar-gap check so "consecutive" means consecutive months
- Naming columns instead of using `SELECT *`
- `EXPLAIN QUERY PLAN` to tell `SCAN` from `SEARCH`
- Adding indexes on a filter column and a join key
- Reading analytical results with pandas and writing a board interpretation for each

## Requirements

```
pip install pandas
```

Python 3.10 or later. SQLite ships with Python, so no database server is needed.
