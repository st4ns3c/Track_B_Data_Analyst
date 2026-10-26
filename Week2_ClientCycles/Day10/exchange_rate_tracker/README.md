# Project 2: Live Exchange Rate Tracker

*Week 2 · Day 10 · Track B project.*

One command shows today's US dollar to Kenyan shilling rate, and what **KES 10,000, 50,000 and 100,000** are worth in dollars.

## The brief

> Call the free exchange rate API at https://open.er-api.com/v6/latest/USD. Parse the JSON and print the USD to KES rate. Then calculate what KES 10,000, KES 50,000, and KES 100,000 are worth in USD. Wrap everything in a try/except block.

| Asked for | Where it's done |
|---|---|
| Call `open.er-api.com/v6/latest/USD` | `requests.get(URL, timeout=10)` |
| Parse the JSON | `response.json()`, then `data["rates"]["KES"]` |
| Print the USD to KES rate | `1 USD = KES 129.87` |
| KES 10,000 / 50,000 / 100,000 in USD | The table: each amount ÷ the rate |
| Wrap everything in try/except | The whole fetch, parse and print sits in one `try`, with an `except` for each thing that can go wrong |

## Setup

```bash
cd Week2_ClientCycles/Day10/exchange_rate_tracker
pip install requests
```

No API key, no `.env`. This endpoint is ExchangeRate-API's free, open one.

## Usage

```bash
python exchange_rate_tracker.py
```

## Example output

From a real run on Mon 26 Oct 2026:

```
Live Exchange Rate Tracker
--------------------------
Rates last updated: Mon, 26 Oct 2026 00:02:31 +0000

1 USD = KES 129.87

          KES            USD
       10,000  =  $    77.00
       50,000  =  $   384.99
      100,000  =  $   769.98

Rates by ExchangeRate-API (https://www.exchangerate-api.com)
```

## How the maths works

The API is asked for rates **based on USD**, so it answers "1 USD = 129.874192 KES". That's shillings *per dollar*. To turn shillings into dollars you **divide**:

```
KES 10,000 ÷ 129.874192 = $77.00
```

(The Week 1 currency tracker asked for rates based on KES instead, so there it multiplied. Same idea, other direction.)

## How it handles problems

Each failure was tested by pointing the script at a broken version of the request:

| Situation | What you see |
|---|---|
| No internet / wrong address | `Couldn't reach the exchange rate service. Check your internet connection.` |
| Server too slow (more than 10 seconds) | `The exchange rate service took too long to answer. Try again in a moment.` |
| Server error, e.g. 404 or 500 | `The exchange rate service returned an error (404). Try again later.` |
| `200 OK` but `"result": "error"` in the body | `Got an answer, but couldn't use it: the service answered: unsupported-code` |
| The reply isn't JSON (e.g. a web page) | `The service sent back something that isn't exchange rates. Try again later.` |
| The reply has no KES rate | `The reply didn't include 'KES', so the rate can't be shown today.` |

Two details I learned while testing:
- **This API reports some errors with a `200 OK`.** Asking for a code that doesn't exist (`/latest/XYZ`) returns `{"result": "error", "error-type": "unsupported-code"}`. So the script checks `result` and doesn't trust the status code alone.
- **The order of the `except` blocks matters.** `requests`' `JSONDecodeError` is also a `ValueError`, so it has to come first, or it gets the more generic message.

## Good to know

- The rates update **once a day** (the time is printed at the top). Running the script ten times in an hour gives the same numbers, so there's no point running it more often.
- The terms of the free endpoint ask for the "Rates by ExchangeRate-API" credit, which is why that line is printed.
- These are mid-market rates. A bank or M-Pesa will give you slightly less when you actually exchange money.

## Files

| File | What it is |
|---|---|
| `exchange_rate_tracker.py` | The script |
| `README.md` | This guide |
