# Day 16: SQL Basics

*Week 4 · SQL for Data · The five Monday-morning questions, answered from one SQLite database.*

A Nairobi wholesale distributor tracks orders in a spreadsheet. Every Monday the sales manager spends about 45 minutes pulling five answers by hand. This folder replaces that routine with a small SQLite database and five SQL queries, run through `pandas.read_sql_query`.

## The brief

Build an `orders` table with `order_id`, `customer_name`, `county`, `product`, `quantity`, `unit_price`, `order_date` and `status`, load at least 20 realistic rows, and answer:

1. All orders from Mombasa county.
2. Top 10 orders by total value.
3. Total revenue per county.
4. All pending orders over KES 50,000.
5. The three best-selling products by quantity.

The exercise table has no `total_value` column, so each query calculates `quantity * unit_price`. One stored price and one stored quantity are safer than a third number that can drift out of step.

## How to run it

```bash
cd Week4_SQLBasics/Day16
python3 generate_orders.py
python3 queries.py
```

`generate_orders.py` rebuilds `data/orders.db` from 28 fixed rows, so every run gives the same database. `queries.py` opens it read-only and prints five result tables. To browse the data by hand, open `data/orders.db` in DB Browser for SQLite and use the **Browse Data** tab.

## What is in this folder

| File | What it is |
|---|---|
| [`generate_orders.py`](generate_orders.py) | Creates `data/orders.db`, the `orders` table and the 28 sample rows. Safe to rerun: it drops and rebuilds the table. |
| [`queries.py`](queries.py) | Runs the five queries with `pandas.read_sql_query` and prints each result with a one-line answer. |
| [`pricing_note.md`](pricing_note.md) | The quote: setup fee and monthly support, kept separate. |
| `data/orders.db` | The generated database. Not committed; rebuild it with the generator. |

## The five answers

| # | Question | Result |
|---|---|---|
| 1 | Orders from Mombasa | **5 orders**, worth **KES 311,500** |
| 2 | Top 10 orders by value | **KES 686,000**, or **71%** of all revenue. Largest: Mutua Wholesale, **KES 144,000** |
| 3 | Revenue per county | **8 counties**. Mombasa leads with **KES 311,500** (32%) |
| 4 | Pending orders over KES 50,000 | **4 orders**, worth **KES 247,100** |
| 5 | Three best-selling products by quantity | **Sugar 1,550 units**, Maize Flour 590, Cooking Oil 218 |

Total database value: **KES 964,550** across 28 orders from 3 August to 20 October 2026.

### 1. All orders from Mombasa county

```sql
SELECT order_id, customer_name, product, quantity, unit_price,
       quantity * unit_price AS total_value, order_date, status
FROM orders
WHERE county = 'Mombasa'
ORDER BY order_date, order_id;
```

| Order | Customer | Product | Qty | Unit price (KES) | Total (KES) | Date | Status |
|---|---|---|---:|---:|---:|---|---|
| 2004 | Hassan Traders | Rice 25kg | 40 | 3,200 | 128,000 | 2026-08-10 | delivered |
| 2007 | Karanja Mart | Cooking Oil 5L | 20 | 850 | 17,000 | 2026-08-17 | pending |
| 2014 | Yusuf Wholesale | Rice 25kg | 20 | 3,200 | 64,000 | 2026-09-04 | pending |
| 2018 | Hassan Traders | Sugar 1kg | 300 | 115 | 34,500 | 2026-09-15 | delivered |
| 2021 | Karanja Mart | Cooking Oil 5L | 80 | 850 | 68,000 | 2026-09-25 | pending |

Mombasa is the strongest county by revenue. Three of its five orders are still pending, and two of those — Karanja Mart's KES 68,000 oil order and Yusuf Wholesale's KES 64,000 rice order — are among the four pending orders over KES 50,000.

### 2. Top 10 orders by total value

```sql
SELECT order_id, customer_name, county, product, quantity,
       quantity * unit_price AS total_value, order_date
FROM orders
ORDER BY total_value DESC, order_id
LIMIT 10;
```

| Order | Customer | County | Product | Qty | Total (KES) | Date |
|---|---|---|---|---:|---:|---|
| 2024 | Mutua Wholesale | Machakos | Rice 25kg | 45 | 144,000 | 2026-10-06 |
| 2004 | Hassan Traders | Mombasa | Rice 25kg | 40 | 128,000 | 2026-08-10 |
| 2021 | Karanja Mart | Mombasa | Cooking Oil 5L | 80 | 68,000 | 2026-09-25 |
| 2014 | Yusuf Wholesale | Mombasa | Rice 25kg | 20 | 64,000 | 2026-09-04 |
| 2028 | Chebet Distributors | Eldoret | Rice 25kg | 18 | 57,600 | 2026-10-20 |
| 2023 | Ochieng Supplies | Kisumu | Sugar 1kg | 500 | 57,500 | 2026-10-02 |
| 2008 | Kiprono Stores | Eldoret | Rice 25kg | 15 | 48,000 | 2026-08-19 |
| 2013 | Chebet Distributors | Eldoret | Sugar 1kg | 400 | 46,000 | 2026-09-02 |
| 2017 | Otieno Wholesale | Kisumu | Rice 25kg | 12 | 38,400 | 2026-09-11 |
| 2018 | Hassan Traders | Mombasa | Sugar 1kg | 300 | 34,500 | 2026-09-15 |

Ten orders carry KES 686,000 of the KES 964,550 total. The top two alone — both rice — are worth KES 272,000, more than a quarter of the book.

### 3. Total revenue per county

```sql
SELECT county,
       COUNT(*) AS order_count,
       SUM(quantity * unit_price) AS total_revenue,
       ROUND(AVG(quantity * unit_price), 0) AS avg_order_value
FROM orders
GROUP BY county
ORDER BY total_revenue DESC;
```

| County | Orders | Revenue (KES) | Avg order (KES) |
|---|---:|---:|---:|
| Mombasa | 5 | 311,500 | 62,300 |
| Eldoret | 4 | 178,000 | 44,500 |
| Machakos | 2 | 165,250 | 82,625 |
| Kisumu | 7 | 163,850 | 23,407 |
| Nairobi | 4 | 57,950 | 14,488 |
| Nyeri | 2 | 40,600 | 20,300 |
| Nakuru | 2 | 32,600 | 16,300 |
| Thika | 2 | 14,800 | 7,400 |

Kisumu places the most orders (7) but ranks fourth on revenue. Mombasa places five and tops the table. Order count and revenue are different measures, which is why the manager needs both columns, not just one.

"Revenue" here is order value: delivered and pending orders together. Nothing in the table is cancelled. A stricter finance report would add `WHERE status = 'delivered'` and report the rest as an order book rather than income.

### 4. Pending orders over KES 50,000

```sql
SELECT order_id, customer_name, county, product,
       quantity * unit_price AS total_value, order_date
FROM orders
WHERE status = 'pending'
  AND quantity * unit_price > 50000
ORDER BY total_value DESC, order_id;
```

| Order | Customer | County | Product | Total (KES) | Date |
|---|---|---|---:|---:|---|
| 2021 | Karanja Mart | Mombasa | Cooking Oil 5L | 68,000 | 2026-09-25 |
| 2014 | Yusuf Wholesale | Mombasa | Rice 25kg | 64,000 | 2026-09-04 |
| 2028 | Chebet Distributors | Eldoret | Rice 25kg | 57,600 | 2026-10-20 |
| 2023 | Ochieng Supplies | Kisumu | Sugar 1kg | 57,500 | 2026-10-02 |

Four orders worth KES 247,100 are waiting to ship. Mombasa holds two of them, so the county's strong revenue position depends partly on orders that have not been delivered yet.

### 5. The three best-selling products by quantity

```sql
SELECT product,
       COUNT(*) AS order_count,
       SUM(quantity) AS total_units,
       SUM(quantity * unit_price) AS total_revenue
FROM orders
GROUP BY product
ORDER BY total_units DESC, product
LIMIT 3;
```

| Product | Orders | Units | Revenue (KES) |
|---|---:|---:|---:|
| Sugar 1kg | 5 | 1,550 | 178,250 |
| Maize Flour 2kg | 5 | 590 | 70,800 |
| Cooking Oil 5L | 6 | 218 | 185,300 |

Sugar moves more than twice as many units as the next product. But "best-selling" depends on the measure. Rice is only fourth by units (150) yet earns **KES 480,000**, half of all revenue, because a 25 kg bag costs KES 3,200. Units answer "what leaves the warehouse fastest"; revenue answers "what pays the bills".

```sql
-- The other half of the answer: revenue by product
SELECT product, SUM(quantity) AS units, SUM(quantity * unit_price) AS revenue
FROM orders
GROUP BY product
ORDER BY revenue DESC;
```

## Two more practice queries

The five questions do not need `OR` or `MAX`, but the lesson covers both. These two checks take a minute:

```sql
-- OR: orders from either of the two biggest markets
SELECT order_id, customer_name, county, quantity * unit_price AS total_value
FROM orders
WHERE county = 'Nairobi' OR county = 'Mombasa'
ORDER BY total_value DESC;
```

Nine orders, worth KES 369,450. The shorter `WHERE county IN ('Nairobi', 'Mombasa')` gives the same result.

```sql
-- MAX: the single largest order, without sorting and limiting
SELECT MAX(quantity * unit_price) AS largest_order
FROM orders;
```

**KES 144,000**, the Mutua Wholesale rice order.

## The SQL used, keyword by keyword

| Keyword | What it does here |
|---|---|
| `SELECT` / `FROM` | Chooses the columns and the table. |
| `WHERE` | Keeps only matching rows, such as `county = 'Mombasa'` or `status = 'pending'`. |
| `AND` / `OR` | Combines conditions. `AND` needs both to be true; `OR` needs either. |
| `ORDER BY ... DESC` | Sorts highest first. `ASC` would sort lowest first. |
| `LIMIT` | Cuts the result to a fixed number of rows. |
| `COUNT`, `SUM`, `AVG`, `MAX` | Collapse many rows into summary numbers. |
| `GROUP BY` | Produces one row per category, such as one row per county or product. |
| `AS` | Names a result column so the report is readable. |
| `quantity * unit_price` | A calculated column; the database works it out at query time. |
| `pandas.read_sql_query` | Runs the SQL and returns a DataFrame for printing or further analysis. |

## Note on the data

The data is **synthetic**, but the shape is deliberate: Mombasa is the strongest county, four pending orders sit above KES 50,000, and the unit/revenue ranking differs by product. The rows are fixed in `generate_orders.py` — no random numbers — so every run reproduces the same totals. Dates run from 3 August to 20 October 2026. Money is in Kenyan shillings.

`data/orders.db` is generated output and is not committed. Run `generate_orders.py` to recreate it.

## Pricing note

The brief also asks what this reporting setup is worth. The short answer: **KES 35,000 to build, KES 9,000 a month to support**, with the setup and support kept separate so the client can see what they pay once and what they pay to keep it running. The full breakdown, assumptions and optional extras are in [`pricing_note.md`](pricing_note.md).

## What was practised

- Creating a table and inserting rows in SQLite
- `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`
- `AND` conditions and numeric comparisons
- `COUNT`, `SUM`, `AVG`, `MAX`
- `GROUP BY` for per-county and per-product summaries
- Calculated columns with `quantity * unit_price`
- Reading query results into pandas with `read_sql_query`
- Saving a reusable script instead of repeating 45 minutes of manual Excel work
- Pricing a small reporting build as a one-off fee plus ongoing support

## Requirements

```
pip install pandas
```

Python 3.10 or later. SQLite ships with Python, so no database server is needed.
