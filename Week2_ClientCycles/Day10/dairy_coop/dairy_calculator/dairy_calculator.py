"""
Dairy Co-op Payment Calculator
------------------------------
A farmer enters their name and the litres they supplied. The tool shows the
total the co-op owes them at the current buying price.

Usage:
    python dairy_calculator.py

Updating the price (once a week, by the co-op manager):
    Open price.txt, replace the number with the new price per litre (e.g. 58),
    save. Nothing else to change. The tool reads it fresh every time it starts.
"""

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# price.txt sits next to this script, so the tool works from any folder.
PRICE_FILE = Path(__file__).parent / "price.txt"

# The price changes weekly. If price.txt is older than this, remind the user
# to check it, so nobody gets paid at last month's rate by mistake.
PRICE_MAX_AGE_DAYS = 7


class PriceError(Exception):
    """Raised when price.txt is missing or wrong, with a message for the user."""


def get_current_price(price_file=PRICE_FILE):
    """Read the price per litre from price.txt.

    There is deliberately no default price. A wrong price means paying 30
    farmers the wrong amount, so it's safer to stop and say what's wrong.
    """
    try:
        # utf-8-sig skips the hidden mark Windows Notepad can put at the start.
        text = price_file.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        raise PriceError(f"Can't find {price_file.name}. Create it next to the tool "
                         "with just this week's price per litre in it, e.g. 55")

    price = parse_number(text)
    if price is None:
        raise PriceError(f"{price_file.name} should contain just the price per litre, "
                         f"e.g. 55, but it says: '{text}'")
    return price


def price_age_days(price_file=PRICE_FILE):
    """How many days ago price.txt was last saved."""
    saved = datetime.fromtimestamp(price_file.stat().st_mtime)
    return (datetime.now() - saved).days, saved


def parse_number(text):
    """Turn what was typed ("1,250", "20.5") into a positive number, or None."""
    try:
        number = float(text.replace(",", "").strip())
    except ValueError:
        return None
    # float() also accepts "nan" and "inf", which are not litres or prices.
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def calculate_payment(litres, price_per_litre):
    """Total owed in KES, rounded to the cent the way a person would (half up).

    Done in Decimal, not float: 3.3 L x KES 57.35 is exactly 189.255, but as a
    float it's 189.25499..., which rounds down and shorts the farmer a cent.
    """
    total = Decimal(str(litres)) * Decimal(str(price_per_litre))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ask_name():
    while True:
        # " ".join(split()) also tidies double spaces: "Jane   Wanjiku" -> "Jane Wanjiku"
        name = " ".join(input("Farmer name: ").split())
        if name:
            return name
        print("  Please type the farmer's name.")


def ask_litres():
    while True:
        litres = parse_number(input("Litres supplied: "))
        if litres is not None:
            return litres
        print("  Please type the litres as a number above 0, e.g. 20 or 12.5")


def print_receipt(name, litres, price):
    total = calculate_payment(litres, price)
    print()
    print(f"  Farmer : {name}")
    print(f"  Litres : {litres:,g}")
    print(f"  Price  : KES {price:,.2f} per litre")
    print(f"  Total  : KES {total:,.2f}")
    print()


def run():
    print("Kiambu Dairy Co-op Payment Calculator")
    print("-------------------------------------")

    try:
        price = get_current_price()
    except PriceError as error:
        print(f"Can't calculate payments yet. {error}")
        raise SystemExit(1)

    age, saved = price_age_days()
    print(f"Current buying price: KES {price:,.2f} per litre (set {saved:%a %d %b %Y})")
    if age > PRICE_MAX_AGE_DAYS:
        print(f"Note: the price was set {age} days ago. Check with the manager that it's still this week's price.")
    print()

    # One farmer after another, so the queue at the collection point can use
    # the same window without restarting the tool.
    while True:
        name = ask_name()
        litres = ask_litres()
        print_receipt(name, litres, price)

        if input("Press Enter for the next farmer, or type q to quit: ").strip().lower() == "q":
            print("Goodbye.")
            break
        print()


if __name__ == "__main__":
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or a closed window: leave quietly instead of showing a traceback.
        print("\nGoodbye.")
