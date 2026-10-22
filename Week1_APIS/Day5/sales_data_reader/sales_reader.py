# Sales Data Reader
#
# Build plan
#   Problem    : A small business keeps its sales in a spreadsheet and wants to know,
#                without opening Excel, how much was sold and who sold the most.
#   Input      : a CSV file with the columns name, county, amount (sales.csv by default,
#                or any other file passed on the command line).
#   Processing : read every row with Python's csv module, skip rows that are broken,
#                add up the amounts, total them per salesperson and per county.
#   Output     : total sales, the top salesperson, and a sales-by-county breakdown.
#
# Usage:
#   python sales_reader.py               reads sales.csv next to this script
#   python sales_reader.py other.csv     reads another file with the same columns

import csv
import sys
from pathlib import Path

# Look for sales.csv next to this script, so it works from any folder.
DEFAULT_FILE = Path(__file__).parent / "sales.csv"
REQUIRED_COLUMNS = {"name", "county", "amount"}


def read_sales(path):
    """Read the CSV and give back a list of clean rows plus a list of problems found.

    Each clean row looks like {"name": "Wanjiku Kamau", "county": "Nairobi", "amount": 45000.0}.
    A broken row (missing name, amount that isn't a number...) is skipped, not fatal.
    """
    sales = []
    problems = []

    # newline="" is what the csv module asks for; utf-8-sig also copes with
    # the hidden marker Excel adds at the start of CSVs it saves.
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        # Check the header first. If a column is missing, nothing below can work.
        columns = {column.strip().lower() for column in (reader.fieldnames or [])}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"The file is missing these columns: {', '.join(sorted(missing))}")

        # start=2 because line 1 is the header, so the first sales row is line 2.
        for line_number, row in enumerate(reader, start=2):
            # Make the keys lowercase and trim spaces, so "Amount " still matches "amount".
            row = {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}

            name = row["name"]
            county = row["county"] or "Unknown"
            if not name:
                problems.append(f"line {line_number}: no name, skipped")
                continue

            # People type money as "45,000" too, so drop the commas before converting.
            try:
                amount = float(row["amount"].replace(",", ""))
            except ValueError:
                problems.append(f"line {line_number}: amount '{row['amount']}' is not a number, skipped")
                continue

            sales.append({"name": name, "county": county, "amount": amount})

    return sales, problems


def total_by(sales, field):
    """Add up the amounts for each value of a field, e.g. per name or per county."""
    totals = {}
    for sale in sales:
        key = sale[field]
        totals[key] = totals.get(key, 0) + sale["amount"]
    return totals


def print_report(sales, path):
    total = sum(sale["amount"] for sale in sales)

    # Group by name first, so someone with several rows is judged on their full total.
    per_person = total_by(sales, "name")
    top_name = max(per_person, key=per_person.get)
    top_amount = per_person[top_name]
    top_county = next(sale["county"] for sale in sales if sale["name"] == top_name)

    per_county = total_by(sales, "county")

    print("=" * 48)
    print(f"  SALES REPORT  ({path.name}, {len(sales)} sales)")
    print("=" * 48)
    print(f"Total sales        : KES {total:,.2f}")
    print(f"Top salesperson    : {top_name} ({top_county})")
    print(f"Their sales        : KES {top_amount:,.2f} ({top_amount / total:.0%} of the total)")
    print()
    print("Sales by county")
    # Biggest county first.
    for county, amount in sorted(per_county.items(), key=lambda item: item[1], reverse=True):
        print(f"  {county:<10} KES {amount:>12,.2f}")
    print("=" * 48)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE

    try:
        sales, problems = read_sales(path)
    except FileNotFoundError:
        print(f"Can't find '{path}'. Check the file name and that you're in the right folder.")
        raise SystemExit(1)
    except ValueError as error:
        print(f"Can't read '{path.name}': {error}")
        print("The first line of the file should be: name,county,amount")
        raise SystemExit(1)

    # Tell the user about skipped rows, so a typo doesn't silently change the totals.
    for problem in problems:
        print(f"Warning: {problem}")
    if problems:
        print()

    if not sales:
        print(f"No usable sales rows in '{path.name}', so there's nothing to add up.")
        raise SystemExit(1)

    print_report(sales, path)


if __name__ == "__main__":
    main()
