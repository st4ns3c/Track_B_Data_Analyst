# Day 2 Exercise: a weather report for several Kenyan towns, using a real API key.
#
# What this script shows:
#   1. The API key lives in a .env file, never in the code.
#   2. The .env file is listed in .gitignore, so it never reaches GitHub.
#   3. Errors are handled on purpose (401, 404, 429, 500, no internet...)
#      so the script explains what went wrong instead of crashing.
#   4. One bad city doesn't stop the rest of the report.

import os

import requests
from dotenv import load_dotenv


# load_dotenv() reads the .env file in this folder and puts every line
# (like OPENWEATHER_API_KEY=...) into the environment, where os.getenv()
# can pick it up. The key never appears in this file.
load_dotenv()
api_key = os.getenv("OPENWEATHER_API_KEY")

# If the key is missing there's no point calling the API at all,
# it would only come back with a 401. Better to say so clearly and stop.
if not api_key:
    print("No API key found.")
    print("Create a .env file in this folder with this line:")
    print("OPENWEATHER_API_KEY=your_key_here")
    raise SystemExit(1)

# The towns I want in my report. "Nairobbi" is misspelled on purpose
# so I can see my 404 handling work without editing the code each time.
CITIES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Nairobbi"]

URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city):
    """Ask OpenWeatherMap for one city's weather.

    Gives back the weather data if it worked, or None if something went wrong
    (after printing a friendly message explaining what happened).
    """
    # Passing the key in params instead of pasting it into the URL string
    # means it won't show up by accident if I ever print the URL.
    params = {"q": city, "appid": api_key, "units": "metric"}

    # Problems can happen before we even get a status code: no internet,
    # or the server taking forever. try/except catches those.
    try:
        response = requests.get(URL, params=params, timeout=10)
    except requests.exceptions.Timeout:
        print(f"{city}: the server took too long to answer. Try again later.")
        return None
    except requests.exceptions.ConnectionError:
        print(f"{city}: couldn't connect. Check your internet connection.")
        return None

    # We got an answer, now check the status code before trusting it.
    if response.status_code == 200:
        return response.json()

    if response.status_code == 401:
        print(f"{city}: API key is invalid or not active yet. Check your .env file.")
    elif response.status_code == 404:
        print(f"{city}: city not found. Check the spelling.")
    elif response.status_code == 429:
        print(f"{city}: too many requests. Wait a bit before trying again.")
    elif response.status_code >= 500:
        print(f"{city}: OpenWeatherMap is having problems ({response.status_code}). Not our fault, try later.")
    else:
        print(f"{city}: unexpected error {response.status_code}: {response.text}")

    return None


print("=" * 50)
print("  Kenya weather report")
print("=" * 50)

# Keep track of how many cities worked, so I can show a summary at the end.
successful = 0

for city in CITIES:
    data = get_weather(city)

    # None means the error was already explained above, so just move on
    # to the next city instead of crashing the whole report.
    if data is None:
        continue

    successful += 1

    # Dig into the JSON "folders" for the values I want.
    name = data["name"]
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    # The API gives a description like "scattered clouds", so I capitalise it.
    description = data["weather"][0]["description"].capitalize()
    # Wind speed comes in metres per second; x 3.6 turns it into km/h.
    wind_kmh = data["wind"]["speed"] * 3.6

    print(f"{name}")
    print(f"   {description}, {temp:.1f}°C (feels like {feels_like:.1f}°C)")
    print(f"   Humidity {humidity}%, wind {wind_kmh:.0f} km/h")

print("=" * 50)
print(f"Got weather for {successful} of {len(CITIES)} towns.")
