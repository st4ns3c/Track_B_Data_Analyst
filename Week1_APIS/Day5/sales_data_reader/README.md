# Sales Data Reader

Reads a sales spreadsheet (CSV) and tells you in one second how much was sold in total, who the top salesperson is, and how each county performed.

*Week 1 · Day 5 · Track B project.*

## The problem it solves

A small business records every sale in a spreadsheet: who made the sale, in which county, and for how much. At the end of the week the owner wants three answers: *How much did we sell? Who sold the most? Which county is doing best?* This script answers all three without opening Excel.

## Setup

No installs needed. It only uses Python's built-in `csv` module.

1. Clone the repo
2. Go into this folder: `cd Week1_APIS/Day5/sales_data_reader`

## Usage

```bash
python sales_reader.py               # reads sales.csv in this folder
python sales_reader.py my_sales.csv  # or any CSV with the same columns
```

The CSV needs this header line, then one sale per row:

```
name,county,amount
Wanjiku Kamau,Nairobi,45000
Otieno Ochieng,Kisumu,32500
```

## Example output

From an actual run on the included `sales.csv`:

```
================================================
  SALES REPORT  (sales.csv, 10 sales)
================================================
Total sales        : KES 385,600.00
Top salesperson    : Amina Hassan (Mombasa)
Their sales        : KES 51,200.00 (13% of the total)

Sales by county
  Nairobi    KES    92,300.00
  Mombasa    KES    88,000.00
  Kisumu     KES    73,650.00
  Nakuru     KES    69,300.00
  Eldoret    KES    62,350.00
================================================
```

## How it handles messy data

Real spreadsheets are never perfect, so the script checks everything:

| Problem in the file | What happens |
|---|---|
| File doesn't exist | `Can't find 'nope.csv'. Check the file name...` |
| A column is missing or the file is empty | Names the missing column(s) and shows the correct header line |
| A row has no name | `Warning: line 3: no name, skipped` |
| Amount isn't a number (`abc`) | `Warning: line 4: amount 'abc' is not a number, skipped` |
| Amount written with commas (`"1,000"`) | Read correctly as 1000 |
| Same person on several rows | Their sales are added together before choosing the top salesperson |
| Header has different capitals/spaces (`Amount `) | Still recognised |
| CSV saved from Excel | Opens fine (the hidden marker Excel adds is handled) |

Skipped rows are always reported, so a typo never silently changes the totals.

## Files

| File | What it is |
|---|---|
| `sales_reader.py` | The script |
| `sales.csv` | Sample data: 10 sales across Nairobi, Mombasa, Kisumu, Nakuru and Eldoret |
| `README.md` | This guide |

## What I practised

- Reading a CSV with `csv.DictReader` so every row is a dictionary
- Validating input: checking the header, converting text to numbers safely with `try`/`except`
- Grouping and totalling data with a dictionary (the same idea as a pivot table or SQL `GROUP BY`)
- Finding the top value with `max(..., key=...)` and sorting results
