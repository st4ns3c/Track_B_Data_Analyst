"""
Live Exchange Rate Tracker
--------------------------
Build plan
  Problem    : someone earning or quoting in shillings wants to know what common
               KES amounts are worth in US dollars at today's rate.
  Input      : nothing to type. One call to the free ExchangeRate-API endpoint.
  Processing : read the USD -> KES rate, then divide each KES amount by it.
  Output     : today's rate and a small KES -> USD table.

Usage:
    python exchange_rate_tracker.py

Requirements:
    pip install requests
    No API key needed: open.er-api.com is the free, open endpoint.
"""

import requests

URL = "https://open.er-api.com/v6/latest/USD"

# The amounts the brief asks for, in shillings.
KES_AMOUNTS = [10_000, 50_000, 100_000]


def main():
    print("Live Exchange Rate Tracker")
    print("--------------------------")

    # Everything that can go wrong (no internet, a slow server, an error answer,
    # a reply without KES in it) is caught here and explained in plain words.
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        # This API can answer 200 OK and still say "error" in the body.
        if data.get("result") != "success":
            raise ValueError(f"the service answered: {data.get('error-type', 'unknown error')}")

        kes_per_usd = data["rates"]["KES"]

        print(f"Rates last updated: {data['time_last_update_utc']}")
        print()
        print(f"1 USD = KES {kes_per_usd:,.2f}")
        print()

        # The rate is shillings per dollar, so KES -> USD means dividing by it.
        print(f"  {'KES':>11}      {'USD':>9}")
        for kes in KES_AMOUNTS:
            usd = kes / kes_per_usd
            print(f"  {kes:>11,}  =  ${usd:>9,.2f}")

        print()
        print("Rates by ExchangeRate-API (https://www.exchangerate-api.com)")

    except requests.exceptions.Timeout:
        print("The exchange rate service took too long to answer. Try again in a moment.")
    except requests.exceptions.ConnectionError:
        print("Couldn't reach the exchange rate service. Check your internet connection.")
    except requests.exceptions.HTTPError as error:
        print(f"The exchange rate service returned an error ({error.response.status_code}). Try again later.")
    except requests.exceptions.JSONDecodeError:
        # Caught before ValueError, because it is one too.
        print("The service sent back something that isn't exchange rates. Try again later.")
    except KeyError as missing:
        print(f"The reply didn't include {missing}, so the rate can't be shown today.")
    except ValueError as error:
        print(f"Got an answer, but couldn't use it: {error}")
    except requests.exceptions.RequestException as error:
        # Anything else requests can raise, e.g. a malformed URL.
        print(f"Couldn't get the rates: {error}")


if __name__ == "__main__":
    main()
