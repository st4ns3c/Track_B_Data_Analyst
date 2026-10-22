# Kenyan Business Currency Tracker

Type a price in Kenyan shillings and instantly see what it's worth in US dollars, euros and British pounds, using today's live exchange rates.

*Week 1 · Day 5 project (Option A): API-Powered Application.*

## The problem it solves

A Kenyan business quoting a client in London, Berlin or New York has to look up three exchange rates and do the maths every time. Rates change daily, so last week's numbers are wrong. This tool fetches today's rates and turns any KES price into a ready-to-send USD/EUR/GBP quote in one step.

## Setup

1. Clone the repo and go into this folder:
   ```bash
   cd Week1_APIS/Day5/currency_tracker
   ```
2. Install the two libraries:
   ```bash
   pip install requests python-dotenv
   ```
3. **(Optional) API key.** The tool works without one, using ExchangeRate-API's open endpoint. To use your own key instead:
   - Sign up free at [exchangerate-api.com](https://www.exchangerate-api.com) (1,500 requests/month)
   - Copy `.env.example` to `.env` and paste your key:
     ```
     EXCHANGERATE_API_KEY=your_key_here
     ```
   `.env` is in `.gitignore`, so your key never reaches GitHub.

## Usage

```bash
python currency_tracker.py           # type prices one after another, Enter on an empty line to quit
python currency_tracker.py 150000    # convert one price and exit
```

Prices can be typed as `150000`, `150,000` or `KES 150,000`.

## Example output

From an actual run:

```
============================================================
  Kenyan Business Currency Tracker
============================================================
Rates last updated: Thu, 22 Oct 2026 00:02:31 +0000
Rates by ExchangeRate-API (www.exchangerate-api.com)

Price in KES (press Enter to quit): 150000

  KES 150,000.00 is worth:
    USD  $      1,155.00   US dollar      (1 KES = 0.007700 USD)
    EUR  €      1,028.25   Euro           (1 KES = 0.006855 EUR)
    GBP  £        862.35   British pound  (1 KES = 0.005749 GBP)


Price in KES (press Enter to quit): abc
That's not a valid price. Type a number above 0, like 150000 or 150,000.

Price in KES (press Enter to quit):
Goodbye!
```

## How it works

1. **One API call per run.** The tool asks ExchangeRate-API for the rates of 1 KES against every currency.
2. **Plain multiplication after that.** Each price you type is multiplied by the USD, EUR and GBP rates. Rates only update once a day, so the tool reuses them for every price instead of spending an API request each time.

| | With a key | Without a key |
|---|---|---|
| URL | `v6.exchangerate-api.com/v6/<KEY>/latest/KES` | `open.er-api.com/v6/latest/KES` |
| Rates are in | `conversion_rates` | `rates` |

## How it handles problems

| Situation | What you see |
|---|---|
| Price isn't a number, or is 0 / negative | `That's not a valid price...` and it asks again |
| Wrong or inactive API key | `The EXCHANGERATE_API_KEY in your .env file is wrong or not active.` |
| Monthly request limit used up (429) | `Too many requests this month for this API key...` |
| Server problem (500+) | `The exchange rate service is having problems...` |
| No internet / timeout | `Couldn't connect to the exchange rate service. Check your internet connection.` |

## Files

| File | What it is |
|---|---|
| `currency_tracker.py` | The tool |
| `.env.example` | Template for the optional API key |
| `.gitignore` | Keeps `.env` out of git |
| `README.md` | This guide |

## What I practised

- Calling a live API with `requests`, with a timeout
- Keeping an optional API key in `.env` with `python-dotenv`
- Reading errors from both the status code *and* the JSON body (this API returns `"result": "error"`)
- Validating user input and accepting the formats people actually type
- Avoiding wasted API calls by fetching once and reusing the data
