"""
Trip Briefing Tool
------------------
Type in a city you're travelling to and get a one-page briefing:
the weather right now, the next 3 days, useful facts about the country,
and what your budget in Kenyan shillings is worth there.

Usage:
    python trip_briefing.py

Requirements:
    pip install requests python-dotenv
    A .env file next to this script containing:
        OPENWEATHER_API_KEY=your_openweathermap_key
        RESTCOUNTRIES_API_KEY=your_restcountries_key

Every briefing is also saved to saved_trips/<city>_<date>.json.
If you're offline, the tool shows the last saved briefing for that city instead.
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

# Work out where this script lives, so the .env file and the saved_trips
# folder are found no matter which folder you run the script from.
BASE_DIR = Path(__file__).parent
SAVE_DIR = BASE_DIR / "saved_trips"

# Load the API keys from .env. They never appear in this code.
load_dotenv(BASE_DIR / ".env")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")
RESTCOUNTRIES_KEY = os.getenv("RESTCOUNTRIES_API_KEY")

# The traveller's home currency. Budgets are typed in this currency.
HOME_CURRENCY = "KES"


# --------------------------------------------------------------------------
# One place to talk to any API
# --------------------------------------------------------------------------

class ApiError(Exception):
    """Raised when an API call fails, carrying a message a normal person understands.

    `offline` is True when the problem is the internet connection itself
    (no answer at all), so the tool knows it can fall back to saved data.
    """

    def __init__(self, message, offline=False):
        super().__init__(message)
        self.offline = offline


def fetch_json(url, params=None, headers=None, what="data"):
    """Call an API and give back the JSON, or raise ApiError with a friendly message.

    Every API call in this tool goes through here, so the error handling
    is written once instead of copy-pasted for each API.
    `what` is a short description (e.g. "weather") used in the messages.
    """
    # Step 1: problems that happen before we even get a reply.
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
    except requests.exceptions.Timeout:
        raise ApiError(f"The {what} service took too long to answer.", offline=True)
    except requests.exceptions.ConnectionError:
        raise ApiError("Couldn't connect to the internet.", offline=True)

    # Step 2: we got a reply. Check the status code before trusting it.
    status = response.status_code
    if status == 200:
        return response.json()
    if status == 401:
        raise ApiError(f"The {what} API key is wrong or not active yet. Check your .env file.")
    if status == 404:
        raise ApiError(f"No {what} found. Check the spelling and try again.")
    if status == 429:
        raise ApiError(f"Too many {what} requests. Wait a minute and try again.")
    if status >= 500:
        raise ApiError(f"The {what} service is having problems right now ({status}). Try later.")
    raise ApiError(f"Unexpected {what} error ({status}).")


# --------------------------------------------------------------------------
# The four API calls. Each one is its own function, so if an API changes
# we only fix that one function.
# --------------------------------------------------------------------------

def get_current_weather(city):
    """API call 1: the weather right now (OpenWeatherMap)."""
    return fetch_json(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": OPENWEATHER_KEY, "units": "metric"},
        what="weather",
    )


def get_forecast(city):
    """API call 2: a 5-day forecast in 3-hour steps (OpenWeatherMap)."""
    return fetch_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"q": city, "appid": OPENWEATHER_KEY, "units": "metric"},
        what="forecast",
    )


def get_country(country_code):
    """API call 3: facts about the country, looked up by its 2-letter code (REST Countries)."""
    data = fetch_json(
        f"https://api.restcountries.com/countries/v5/codes.alpha_2/{country_code}",
        # Only ask for the fields we use. Smaller response, faster tool.
        params={"response_fields": "names,capitals,currencies,languages,"
                                   "timezones,calling_codes,cars,region,flag.emoji"},
        headers={"Authorization": f"Bearer {RESTCOUNTRIES_KEY}"},
        what="country",
    )
    countries = data["data"]["objects"]
    if not countries:
        raise ApiError(f"No country info found for code {country_code}.")
    return countries[0]


def convert_currency(amount, from_code, to_code):
    """API call 4: convert the budget into the local currency (REST Countries Currencies)."""
    data = fetch_json(
        "https://api.restcountries.com/currencies/v1/convert",
        params={"from": from_code, "to": to_code, "amount": amount},
        headers={"Authorization": f"Bearer {RESTCOUNTRIES_KEY}"},
        what="currency",
    )
    return data["data"]["objects"][0]


# --------------------------------------------------------------------------
# Saving and loading briefings (JSON files)
# --------------------------------------------------------------------------

def make_slug(city):
    """Turn "New York" into "new_york" so it's safe to use in a filename."""
    return "_".join(city.lower().split())


def save_briefing(briefing, city):
    """Save everything we collected to saved_trips/<city>_<date>.json."""
    SAVE_DIR.mkdir(exist_ok=True)
    filename = SAVE_DIR / f"{make_slug(city)}_{datetime.now():%Y-%m-%d}.json"
    with open(filename, "w", encoding="utf-8") as f:
        # indent=2 makes the file readable if you open it yourself.
        json.dump(briefing, f, indent=2, ensure_ascii=False)
    return filename


def load_latest_briefing(city):
    """Find the newest saved briefing for this city, or None if there isn't one."""
    # The date in the filename is YYYY-MM-DD, so sorting by name = sorting by date.
    files = sorted(SAVE_DIR.glob(f"{make_slug(city)}_*.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Turning raw data into something readable
# --------------------------------------------------------------------------

def summarise_forecast(forecast, days=3):
    """Squash the 3-hourly forecast into one line per day.

    The API gives ~40 readings (every 3 hours for 5 days). For each day we
    want the lowest and highest temperature, the most common sky condition,
    and the highest chance of rain. Today is skipped since it's half over.
    """
    # The forecast times are in UTC. The city's offset from UTC (in seconds)
    # lets us group readings by the city's own calendar day.
    offset = timedelta(seconds=forecast["city"]["timezone"])
    today = (datetime.now(timezone.utc) + offset).date()

    by_day = {}
    for reading in forecast["list"]:
        utc_time = datetime.strptime(reading["dt_txt"], "%Y-%m-%d %H:%M:%S")
        local_day = (utc_time + offset).date()
        if local_day == today:
            continue
        by_day.setdefault(local_day, []).append(reading)

    summary = []
    for day in sorted(by_day)[:days]:
        readings = by_day[day]
        temps = [r["main"]["temp"] for r in readings]
        conditions = Counter(r["weather"][0]["description"] for r in readings)
        summary.append({
            "day": day.strftime("%a %d %b"),
            "low": min(temps),
            "high": max(temps),
            "condition": conditions.most_common(1)[0][0].capitalize(),
            # "pop" = probability of precipitation, from 0 to 1.
            "rain_chance": max(r.get("pop", 0) for r in readings) * 100,
        })
    return summary


def local_time_text(utc_offset_seconds):
    """What time is it in the destination right now?"""
    now_there = datetime.now(timezone.utc) + timedelta(seconds=utc_offset_seconds)
    return now_there.strftime("%A %I:%M %p")


def print_briefing(briefing):
    """Print the briefing in plain English. No JSON shown to the user."""
    weather = briefing["weather"]
    country = briefing.get("country")
    conversion = briefing.get("conversion")

    flag = country["flag"]["emoji"] if country else ""
    place = f"{weather['name']}, {country['names']['common'] if country else weather['sys']['country']}"

    print()
    print("=" * 56)
    print(f"  TRIP BRIEFING: {place} {flag}")
    if briefing.get("offline"):
        print(f"  (OFFLINE: showing saved data from {briefing['saved_at']})")
    print("=" * 56)

    # --- Weather now ---
    print("\nWEATHER NOW")
    print(f"  Local time    : {local_time_text(weather['timezone'])}")
    print(f"  Conditions    : {weather['weather'][0]['description'].capitalize()}")
    print(f"  Temperature   : {weather['main']['temp']:.0f}°C "
          f"(feels like {weather['main']['feels_like']:.0f}°C)")
    print(f"  Humidity      : {weather['main']['humidity']}%")
    # The API gives wind in metres per second. x 3.6 = km/h.
    print(f"  Wind          : {weather['wind']['speed'] * 3.6:.0f} km/h")

    # --- Next few days ---
    forecast = briefing.get("forecast")
    if forecast:
        print("\nNEXT 3 DAYS")
        for day in summarise_forecast(forecast):
            print(f"  {day['day']}  : {day['low']:.0f}–{day['high']:.0f}°C, "
                  f"{day['condition'].lower()}, {day['rain_chance']:.0f}% chance of rain")

    # --- Country facts ---
    if country:
        capital = country["capitals"][0]["name"] if country["capitals"] else "None"
        languages = ", ".join(lang["name"] for lang in country["languages"])
        currencies = ", ".join(f"{c['name']} ({c['code']})" for c in country["currencies"])
        print("\nABOUT THE COUNTRY")
        print(f"  Capital       : {capital}")
        print(f"  Languages     : {languages}")
        print(f"  Currency      : {currencies}")
        print(f"  Dialling code : +{country['calling_codes'][0]}")
        print(f"  Cars drive on : the {country['cars']['driving_side']}")
    else:
        print("\n(Country info unavailable right now.)")

    # --- Money ---
    if conversion:
        print("\nYOUR BUDGET")
        print(f"  {conversion['from']['code']} {conversion['amount']:,.0f}  ≈  "
              f"{conversion['to']['symbol']}{conversion['result']:,.2f} {conversion['to']['code']}")
        print(f"  (1 {conversion['from']['code']} = {conversion['rate']:.4f} {conversion['to']['code']})")

    print("=" * 56)


# --------------------------------------------------------------------------
# Asking the user for input
# --------------------------------------------------------------------------

def ask_budget():
    """Ask for a budget in KES. Blank means skip. Keeps asking until it's a number."""
    while True:
        text = input(f"Your budget in {HOME_CURRENCY} (press Enter to skip): ").strip()
        if not text:
            return None
        # Allow people to type 50,000 with a comma.
        text = text.replace(",", "")
        try:
            amount = float(text)
        except ValueError:
            print("  That's not a number. Try something like 50000.")
            continue
        if amount <= 0:
            print("  The budget must be more than 0.")
            continue
        return amount


# --------------------------------------------------------------------------
# Putting it all together
# --------------------------------------------------------------------------

def build_briefing(city, budget):
    """Chain the API calls: each answer gives us what we need for the next one.

    weather -> country code -> country info -> local currency -> budget conversion
    """
    # The weather call must work, otherwise we have nothing to show.
    # If it fails, the ApiError goes up to run_tool() to deal with.
    weather = get_current_weather(city)

    briefing = {
        "saved_at": f"{datetime.now():%Y-%m-%d %H:%M}",
        "city": city,
        "weather": weather,
        "forecast": None,
        "country": None,
        "conversion": None,
    }

    # The rest are "nice to have". If one fails we say so and carry on,
    # instead of throwing away the whole briefing.
    try:
        briefing["forecast"] = get_forecast(city)
    except ApiError as error:
        print(f"  Note: forecast skipped. {error}")

    # CHAINING: the weather response tells us the country code (e.g. "KE").
    country_code = weather["sys"]["country"]
    try:
        briefing["country"] = get_country(country_code)
    except ApiError as error:
        print(f"  Note: country info skipped. {error}")

    # CHAINING again: the country info tells us the local currency.
    if budget and briefing["country"]:
        local_currency = briefing["country"]["currencies"][0]["code"]
        if local_currency == HOME_CURRENCY:
            print(f"  Note: they use {HOME_CURRENCY} there too, no conversion needed.")
        else:
            try:
                briefing["conversion"] = convert_currency(budget, HOME_CURRENCY, local_currency)
            except ApiError as error:
                print(f"  Note: currency conversion skipped. {error}")

    return briefing


def run_tool():
    print("Trip Briefing Tool")
    print("------------------")

    # Stop early with clear instructions if the keys aren't set up.
    missing = [name for name, value in [("OPENWEATHER_API_KEY", OPENWEATHER_KEY),
                                        ("RESTCOUNTRIES_API_KEY", RESTCOUNTRIES_KEY)]
               if not value]
    if missing:
        print("Missing API key(s): " + ", ".join(missing))
        print(f"Add them to {BASE_DIR / '.env'} (see README.md).")
        return

    # Keep going until the user is done, so they can check several trips.
    while True:
        city = input("\nWhere are you travelling to? (press Enter to quit): ").strip()
        if not city:
            print("Safe travels!")
            break

        budget = ask_budget()
        print(f"\nPreparing your briefing for {city}...")

        try:
            briefing = build_briefing(city, budget)
        except ApiError as error:
            print(f"Sorry: {error}")
            # If the problem is the internet, try the last saved briefing.
            if error.offline:
                saved = load_latest_briefing(city)
                if saved:
                    saved["offline"] = True
                    print_briefing(saved)
                else:
                    print(f"No saved briefing for {city} to show offline either.")
            continue

        print_briefing(briefing)
        saved_to = save_briefing(briefing, city)
        print(f"Saved to {saved_to.relative_to(BASE_DIR)}")


# Only run the tool when this file is run directly
# (not when another script imports its functions).
if __name__ == "__main__":
    run_tool()
