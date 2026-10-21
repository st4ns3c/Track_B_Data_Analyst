# Trip Briefing Tool

A command-line tool that gives you a one-page briefing for any city you're travelling to: the weather now, the next 3 days, the key facts about the country, and what your budget in Kenyan shillings is worth there.

*Week 1 · Day 3 exercise: Building Useful Tools with APIs.*

## The problem it solves

Before a trip you usually open four different websites: one for the weather, one for the forecast, one to look up the country (language, currency, which side of the road they drive on…), and a currency converter. This tool does all of that in one step from the terminal, and keeps a copy of each briefing so you can still read it when you're offline.

## What it does

1. Asks where you're going and (optionally) your budget in KES.
2. Chains four live API calls, each one feeding the next:

   ```
   City name
     └─> 1. Current weather   (OpenWeatherMap)  ──> gives the country code, e.g. "JP"
     └─> 2. 3-day forecast    (OpenWeatherMap)
                                    country code ──> 3. Country facts  (REST Countries)
                                                        └─> gives the currency, e.g. "JPY"
                                    KES budget + currency ──> 4. Conversion (REST Countries Currencies)
   ```

3. Prints a clean, plain-English briefing.
4. Saves everything to `saved_trips/<city>_<date>.json`.
5. If there's no internet, it shows the last saved briefing for that city instead.

## Example

```
Where are you travelling to? (press Enter to quit): Tokyo
Your budget in KES (press Enter to skip): 50,000

Preparing your briefing for Tokyo...

========================================================
  TRIP BRIEFING: Tokyo, Japan 🇯🇵
========================================================

WEATHER NOW
  Local time    : Wednesday 07:55 PM
  Conditions    : Clear sky
  Temperature   : 25°C (feels like 25°C)
  Humidity      : 70%
  Wind          : 46 km/h

NEXT 3 DAYS
  Thu 22 Oct  : 18–24°C, overcast clouds, 0% chance of rain
  Fri 23 Oct  : 16–21°C, scattered clouds, 0% chance of rain
  Sat 24 Oct  : 17–20°C, moderate rain, 100% chance of rain

ABOUT THE COUNTRY
  Capital       : Tokyo
  Languages     : Japanese
  Currency      : Japanese yen (JPY)
  Dialling code : +81
  Cars drive on : the left

YOUR BUDGET
  KES 50,000  ≈  ¥60,873.15 JPY
  (1 KES = 1.2175 JPY)
========================================================
Saved to saved_trips/tokyo_2026-10-21.json
```

## How to run it

**1. Install the libraries**

```bash
pip install requests python-dotenv
```

**2. Get two free API keys**

| API | Sign up | Free tier |
|---|---|---|
| OpenWeatherMap | [openweathermap.org](https://openweathermap.org) | 1,000 calls/day (new keys can take up to 2 hours to activate) |
| REST Countries | [restcountries.com/sign-up](https://restcountries.com/sign-up) | 1,000 calls/month, covers both the Countries and Currencies APIs |

**3. Create a `.env` file** in this folder (next to `trip_briefing.py`):

```
OPENWEATHER_API_KEY=your_openweathermap_key
RESTCOUNTRIES_API_KEY=your_restcountries_key
```

No quotes, no spaces around `=`. The `.env` file is listed in `.gitignore`, so your keys never get pushed to GitHub.

**4. Run it**

```bash
python trip_briefing.py
```

Type a city, optionally a budget, and press Enter on an empty line to quit.

## How it handles problems

The tool explains what went wrong instead of crashing:

| Situation | What you see |
|---|---|
| City doesn't exist / misspelled (404) | `No weather found. Check the spelling and try again.` and it asks again |
| Wrong or inactive API key (401) | `The weather API key is wrong or not active yet. Check your .env file.` |
| Too many requests (429) | `Too many weather requests. Wait a minute and try again.` |
| API server problem (500+) | `The weather service is having problems right now…` |
| No internet / timeout | Shows the last saved briefing for that city, marked **OFFLINE** |
| Missing key in `.env` | Lists which key is missing before making any calls |
| Budget isn't a number | `That's not a number. Try something like 50000.` and asks again |
| Forecast, country or currency call fails | Shows a short note and still prints the rest of the briefing |
| Destination already uses KES | Skips the conversion and says why |

## Files

| File | What it is |
|---|---|
| `trip_briefing.py` | The tool |
| `README.md` | This guide |
| `.gitignore` | Keeps `.env` and `saved_trips/` out of git |
| `.env` | Your API keys (you create it; never committed) |
| `saved_trips/` | Saved briefings as JSON (created automatically) |

## What I practised

- Taking user input instead of hardcoded values, and validating it
- Chaining API calls: the output of one request is the input to the next
- Keeping each API call in its own function, with one shared error handler
- Reading API keys from `.env` with `python-dotenv`
- Saving responses with `json.dump()` and loading them back with `json.load()`
- Turning 40 raw 3-hourly forecast readings into a 3-line daily summary
