"""
Kenyan Business Currency Tracker
--------------------------------
Build plan
  Problem    : A Kenyan business quoting clients abroad needs to know what its
               KES prices are worth in dollars, euros and pounds today.
  Input      : a price in KES, typed in (or passed on the command line).
  Processing : one call to ExchangeRate-API for today's KES rates, then simple
               multiplication for USD, EUR and GBP.
  Output     : a small quote table with each converted price and the rate used.

Usage:
    python currency_tracker.py            asks for prices until you press Enter
    python currency_tracker.py 150000     converts one price and exits

Requirements:
    pip install requests python-dotenv
    Optional: EXCHANGERATE_API_KEY in a .env file (free key from exchangerate-api.com).
    Without a key the tool uses ExchangeRate-API's open endpoint instead.
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Read the .env next to this script, so it works from any folder.
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("EXCHANGERATE_API_KEY")

HOME_CURRENCY = "KES"

# The currencies clients abroad usually ask for, with the symbol to show.
TARGET_CURRENCIES = {
    "USD": ("US dollar", "$"),
    "EUR": ("Euro", "€"),
    "GBP": ("British pound", "£"),
}


class RatesError(Exception):
    """Raised when the rates can't be fetched, with a message for the user."""


def get_rates():
    """Fetch today's rates for 1 KES and return (rates, last_updated).

    With a key we use the keyed v6 API (1,500 free requests a month).
    Without one we use the open endpoint, which needs no sign-up and updates daily.
    The two return the same thing, just under a different name.
    """
    if API_KEY:
        url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{HOME_CURRENCY}"
        rates_field = "conversion_rates"
    else:
        url = f"https://open.er-api.com/v6/latest/{HOME_CURRENCY}"
        rates_field = "rates"

    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.Timeout:
        raise RatesError("The exchange rate service took too long to answer. Try again in a moment.")
    except requests.exceptions.ConnectionError:
        raise RatesError("Couldn't connect to the exchange rate service. Check your internet connection.")

    if response.status_code == 429:
        raise RatesError("Too many requests this month for this API key. Try again later.")
    if response.status_code >= 500:
        raise RatesError(f"The exchange rate service is having problems ({response.status_code}). Try later.")

    # This API also puts errors in the body as {"result": "error", "error-type": "..."},
    # often with a 403, so read the body before deciding what went wrong.
    try:
        data = response.json()
    except ValueError:
        raise RatesError(f"Got an unreadable answer from the exchange rate service ({response.status_code}).")

    if data.get("result") != "success":
        error_type = data.get("error-type", f"status {response.status_code}")
        if error_type in ("invalid-key", "inactive-account"):
            raise RatesError("The EXCHANGERATE_API_KEY in your .env file is wrong or not active.")
        raise RatesError(f"The exchange rate service returned an error: {error_type}")

    return data[rates_field], data["time_last_update_utc"]


def parse_amount(text):
    """Turn what the user typed ("150,000", "KES 2500") into a number, or None if it isn't one."""
    cleaned = text.upper().replace("KES", "").replace("KSH", "").replace(",", "").strip()
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    # A negative price makes no sense for a quote.
    return amount if amount > 0 else None


def print_quote(amount, rates):
    print()
    print(f"  KES {amount:,.2f} is worth:")
    for code, (name, symbol) in TARGET_CURRENCIES.items():
        rate = rates[code]
        print(f"    {code}  {symbol}{amount * rate:>14,.2f}   {name:<14} (1 KES = {rate:.6f} {code})")
    print()


def main():
    print("=" * 60)
    print("  Kenyan Business Currency Tracker")
    print("=" * 60)

    # Quick mode: python currency_tracker.py 150000
    # Check the price before calling the API, so a typo doesn't waste a request.
    quick_amount = None
    if len(sys.argv) > 1:
        quick_amount = parse_amount(" ".join(sys.argv[1:]))
        if quick_amount is None:
            print(f"'{' '.join(sys.argv[1:])}' isn't a price. Try something like 150000.")
            raise SystemExit(1)

    # Fetch the rates ONCE and reuse them for every price. The rates only change
    # once a day, so calling the API for every price would just waste requests.
    try:
        rates, last_updated = get_rates()
    except RatesError as error:
        print(f"Sorry, couldn't get today's rates. {error}")
        raise SystemExit(1)

    print(f"Rates last updated: {last_updated}")
    print("Rates by ExchangeRate-API (www.exchangerate-api.com)")

    if quick_amount is not None:
        print_quote(quick_amount, rates)
        return

    # Interactive mode: keep converting until the user presses Enter on an empty line.
    while True:
        text = input("\nPrice in KES (press Enter to quit): ").strip()
        if not text:
            print("Goodbye!")
            break

        amount = parse_amount(text)
        if amount is None:
            print("That's not a valid price. Type a number above 0, like 150000 or 150,000.")
            continue

        print_quote(amount, rates)


if __name__ == "__main__":
    main()
