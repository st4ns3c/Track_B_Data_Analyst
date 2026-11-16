# Day 17: Joins and Subqueries

*Week 4 · SQL for Data · Two tables, three questions, and the customers behind the revenue.*

Day 16 kept everything in one `orders` table, with the customer name and county typed on every row. That is how a spreadsheet works. A database splits the repeating customer details into their own table and points at them with a key. Today's work joins the two back together.

## The brief

The same Nairobi distributor wants to know which customers drive revenue and whether the best customers cluster in one county. The data is in two tables: `orders` and `customers` (`customer_id`, `customer_name`, `county`, `account_tier`).

Write three queries:

1. A JOIN returning each order with the customer's account tier.
2. Total spend per customer, filtered to customers with more than three orders.
3. The top customer per county, using a subquery or window function.

Run all three with pandas and print clean results. Explain what each query answers and why a sales manager cares.

## How to run it

```bash
cd Week4_SQLBasics/Day17
python3 generate_data.py
python3 queries.py
```

`generate_data.py` rebuilds `data/distributor.db` from 14 fixed customers and 44 fixed orders. `queries.py` opens it read-only, prints the three exercise queries and adds one LEFT JOIN check for dormant customers. To browse the tables by hand, open `data/distributor.db` in DB Browser for SQLite.

## What is in this folder

| File | What it is |
|---|---|
| [`generate_data.py`](generate_data.py) | Creates `data/distributor.db`, both tables and the sample rows. Safe to rerun: it drops and rebuilds both tables. |
| [`queries.py`](queries.py) | Runs the three queries plus the dormant-customer check with `pandas.read_sql_query`. |
| `data/distributor.db` | The generated database. Not committed; rebuild it with the generator. |

## The data model

| `customers` (14 rows) | `orders` (44 rows) |
|---|---|
| `customer_id` — primary key | `order_id` — primary key |
| `customer_name` | `customer_id` — foreign key to customers |
| `county` | `product` |
| `account_tier` — bronze, silver or gold | `quantity`, `unit_price` |
| | `order_date`, `status` |

The join key is `customer_id`, not the customer name. Names can be typed differently, changed or duplicated; an integer key cannot. The customer's county and tier are stored once, on the customer row, so there is only one version of the truth.

One customer, **Baraka Distributors**, is a gold account in Nairobi with **zero orders**. That row exists on purpose: it is the difference between an INNER JOIN and a LEFT JOIN.

Total order value: **KES 1,387,000** across 44 orders from 3 August to 1 October 2026.

## Query 1: every order with its account tier

```sql
SELECT o.order_id,
       c.customer_name,
       c.account_tier,
       o.product,
       o.order_date,
       o.quantity * o.unit_price AS order_value,
       o.status
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
ORDER BY o.order_id;
```

44 rows. The first ten:

| Order | Customer | Tier | Product | Date | Value (KES) | Status |
|---:|---|---|---|---|---:|---|
| 3001 | Kamau Stores | silver | Maize Flour 2kg | 2026-08-03 | 7,200 | delivered |
| 3002 | Otieno Wholesale | gold | Rice 25kg | 2026-08-04 | 80,000 | delivered |
| 3003 | Hassan Traders | gold | Rice 25kg | 2026-08-05 | 128,000 | delivered |
| 3004 | Kiprono Stores | bronze | Rice 25kg | 2026-08-06 | 48,000 | delivered |
| 3005 | Ochieng Supplies | silver | Sugar 1kg | 2026-08-07 | 46,000 | delivered |
| 3006 | Waweru Ltd | bronze | Maize Flour 2kg | 2026-08-10 | 12,000 | delivered |
| 3007 | Njoroge Supplies | silver | Wheat Flour 2kg | 2026-08-11 | 22,400 | delivered |
| 3008 | Mutua Wholesale | gold | Rice 25kg | 2026-08-12 | 96,000 | delivered |
| 3009 | Chebet Distributors | gold | Sugar 1kg | 2026-08-13 | 46,000 | delivered |
| 3010 | Njeri Enterprises | bronze | Wheat Flour 2kg | 2026-08-14 | 9,600 | delivered |

**What it answers:** one row per order, with the tier that belongs to that customer. All 44 orders matched a customer; there are no orphan orders.

**Why the sales manager cares:** this is the base table for any tier-based report. The largest single order is Hassan Traders' **KES 128,000** rice order, a gold account. Without the join, the orders table only has `customer_id`, so the tier is invisible.

`INNER JOIN` is right here because an order without a valid customer is a data error, not a business case. The foreign key and the `PRAGMA foreign_key_check` in `queries.py` catch an orphan order if one ever appears.

## Query 2: frequent customers, by total spend

```sql
SELECT c.customer_name,
       c.county,
       c.account_tier,
       COUNT(o.order_id) AS order_count,
       SUM(o.quantity * o.unit_price) AS total_spend,
       ROUND(AVG(o.quantity * o.unit_price), 0) AS avg_order
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name, c.county, c.account_tier
HAVING COUNT(o.order_id) > 3
ORDER BY total_spend DESC;
```

| Customer | County | Tier | Orders | Total spend (KES) | Avg order (KES) |
|---|---|---|---:|---:|---:|
| Chebet Distributors | Eldoret | gold | 5 | 209,750 | 41,950 |
| Mutua Wholesale | Machakos | gold | 4 | 207,250 | 51,813 |
| Hassan Traders | Mombasa | gold | 4 | 204,550 | 51,138 |
| Otieno Wholesale | Kisumu | gold | 5 | 179,300 | 35,860 |
| Ochieng Supplies | Kisumu | silver | 4 | 120,050 | 30,013 |
| Kamau Stores | Nairobi | silver | 4 | 84,950 | 21,238 |

**What it answers:** six customers have placed more than three orders. Together they account for **KES 1,005,850**, or **72.5%** of all revenue. Chebet Distributors is the largest at **KES 209,750** from five orders.

**Why the sales manager cares:** these are the accounts worth protecting. Four of the six are gold; Ochieng Supplies and Kamau Stores are silver but still place four orders each, which makes them candidates for an upgrade conversation.

There is a trap in the filter. **Kiprono Stores spent KES 92,600 in only three orders**, so the "more than three orders" rule excludes it — even though it spent more than Kamau Stores (KES 84,950 in four orders). Order count measures **frequency**, not **value**. This query is a loyalty list, not a complete top-spend list. A manager who treats it as the latter will miss a quiet, high-value bronze account.

`WHERE` cannot do this filter: `WHERE COUNT(...) > 3` is invalid because `WHERE` runs before the rows are grouped. `HAVING` runs after `GROUP BY`, which is exactly what a filter on an aggregate needs.

## Query 3: the top customer in each county

```sql
WITH customer_totals AS (
    SELECT c.customer_id,
           c.customer_name,
           c.county,
           c.account_tier,
           COUNT(o.order_id) AS order_count,
           SUM(o.quantity * o.unit_price) AS total_spend
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name, c.county, c.account_tier
)
SELECT county, customer_name, account_tier, order_count, total_spend
FROM customer_totals ct
WHERE total_spend = (
    SELECT MAX(total_spend)
    FROM customer_totals
    WHERE county = ct.county
)
ORDER BY total_spend DESC;
```

| County | Customer | Tier | Orders | Total spend (KES) |
|---|---|---|---:|---:|
| Eldoret | Chebet Distributors | gold | 5 | 209,750 |
| Machakos | Mutua Wholesale | gold | 4 | 207,250 |
| Mombasa | Hassan Traders | gold | 4 | 204,550 |
| Kisumu | Otieno Wholesale | gold | 5 | 179,300 |
| Nairobi | Kamau Stores | silver | 4 | 84,950 |
| Nakuru | Njoroge Supplies | silver | 2 | 56,900 |
| Nyeri | Njeri Enterprises | bronze | 2 | 33,400 |
| Thika | Mwangi Mini Mart | silver | 2 | 22,800 |

**What it answers:** eight counties each have one top account. Chebet Distributors in Eldoret is the biggest single account at **KES 209,750**, 15.1% of all revenue. The top three accounts, in Eldoret, Machakos and Mombasa, are within **KES 5,200** of each other and together carry **45%** of revenue.

**Why the sales manager cares:** the answer to "do the top customers concentrate in one county?" is **no**. The three largest accounts sit in three different counties, so the business is not dependent on one region. But every county has a clear anchor account. In Nairobi, Kamau Stores (KES 84,950) is well ahead of Waweru Ltd (KES 53,700); in Kisumu, Otieno Wholesale (KES 179,300) leads Ochieng Supplies (KES 120,050); in Mombasa, Hassan Traders (KES 204,550) leads Karanja Mart (KES 82,300); in Eldoret, Chebet (KES 209,750) leads Kiprono (KES 92,600).

The `WITH` block is a **common table expression (CTE)** — a named subquery that can be used twice. The `WHERE total_spend = (SELECT MAX(...) ...)` is a **correlated subquery**: for each customer row, it finds the best spend in that customer's county. If two customers tied, both would appear. No county ties here.

SQLite also supports window functions. `ROW_NUMBER() OVER (PARTITION BY county ORDER BY total_spend DESC)` would rank customers inside each county and let you keep `rank = 1`. The CTE version stays closer to today's subquery lesson and is easier to read for a one-off report.

## Bonus: the customer who never ordered

```sql
SELECT c.customer_name, c.county, c.account_tier
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_name;
```

| Customer | County | Tier |
|---|---|---|
| Baraka Distributors | Nairobi | gold |

**What it answers:** Baraka Distributors is a gold account in Nairobi with zero orders. `LEFT JOIN` keeps every customer, including those with no match on the right; `WHERE o.order_id IS NULL` then keeps only the unmatched ones.

**Why the sales manager cares:** this is the first sales call of the week. A gold-tier customer who has never ordered is a warm lead that the order report alone would never show. The same pattern finds products never sold, counties with no deliveries, or staff with no sales.

## Join and subquery cheat sheet

| Pattern | What it returns | Where it is used |
|---|---|---|
| `INNER JOIN ... ON` | Only rows with a match in both tables | Queries 1, 2 and 3 |
| `LEFT JOIN ... WHERE right.key IS NULL` | Rows in the left table with no match on the right | Dormant-customer bonus |
| Subquery in `WHERE` | Compares each row with a value calculated by another query | Query 3 |
| CTE (`WITH`) | Names a subquery so it can be reused and read top to bottom | Query 3 |
| `GROUP BY` + `HAVING` | One row per group, then filters the groups | Query 2 |
| `COUNT`, `SUM`, `AVG` | Collapses many order rows into customer totals | Queries 2 and 3 |

Three rules of thumb:

- **Join** when you need columns from another table.
- **Subquery** when you need a number or list to compare against, such as an average or a per-county maximum.
- **LEFT JOIN** when the missing row is the answer, or when you must keep every customer whether they ordered or not.

Join on the key, not the name. The whole point of splitting the tables is that the customer's details live in one place.

## Pricing note

**KES 45,000 to build and KES 10,000 a month to support** — about KES 10,000 more than the Day 16 single-table setup, because the customer table, keys, joins and data-quality checks add a day of modelling and testing.

## Note on the data

The data is **synthetic** and deliberately shaped: 14 customers, 44 orders, one dormant gold customer, and six customers above the three-order threshold. The rows are fixed in `generate_data.py` — no random numbers — so every run reproduces the same totals. Dates run from 3 August to 1 October 2026. Money is in Kenyan shillings.

"Spend" is order value: delivered and pending orders together. Nothing in the table is cancelled. A finance report would add `WHERE status = 'delivered'` and treat the rest as an order book rather than income.

`data/distributor.db` is generated output and is not committed. Run `generate_data.py` to recreate it.

## What was practised

- Splitting repeating customer details into a second table
- Designing a primary key and a foreign key
- `INNER JOIN` to attach account tiers to orders
- `LEFT JOIN` with `IS NULL` to find missing rows
- `GROUP BY` and `HAVING` to filter aggregated customer totals
- A CTE and a correlated subquery to find the top customer per county
- Reading joined results into pandas with `read_sql_query`
- Separating order frequency from order value when interpreting a report
- Pricing a two-table reporting layer

## Requirements

```
pip install pandas
```

Python 3.10 or later. SQLite ships with Python, so no database server is needed.
