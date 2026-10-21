# Day 1 Exercise: a simple weather report for Nairobi.
#
# I'm using Open-Meteo (open-meteo.com) because it's free and doesn't need
# an API key, so there's nothing to sign up for or hide from GitHub.
# The goal: ask the API for live weather, then print it in a way that
# someone who has never seen JSON can read it easily.

from datetime import datetime

import requests


# Where do we want the weather for? Open-Meteo doesn't take city names,
# it wants coordinates. I got these from the REST Countries response
# earlier (Nairobi's capital coordinates: lat -1.28, lng 36.82).
CITY = "Nairobi"
LATITUDE = -1.28
LONGITUDE = 36.82

# The base URL is the "address" of the API. Everything else we want
# goes in as parameters (the bit after the ? in a URL).
url = "https://api.open-meteo.com/v1/forecast"

# Instead of building one long messy URL by hand, I give requests a
# dictionary and it builds the URL for me. Much easier to read and change.
params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    # What I want to know right now:
    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
    # And a short look at the next few days:
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    "timezone": "Africa/Nairobi",  # so the times come back in Kenyan time
    "forecast_days": 3,
}

# The weather API sends back a number (a "WMO weather code") instead of
# words like "sunny". This little lookup table turns the number into
# something a human understands. I only listed the common ones.
WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

# Send the request. The timeout means "give up after 10 seconds" so the
# program doesn't just hang forever if the internet is slow.
response = requests.get(url, params=params, timeout=10)

# Always check the status code before trusting the data.
# 200 means OK. Anything else means something went wrong.
if response.status_code != 200:
    print("Sorry, couldn't get the weather right now.")
    print("Status code:", response.status_code)
    print("What the server said:", response.text)
    raise SystemExit(1)

data = response.json()

# The response is like a set of folders. "current" holds right-now values,
# "daily" holds lists, one item per day.
current = data["current"]
daily = data["daily"]

# Pull out just the values I care about.
temperature = current["temperature_2m"]
feels_like = current["apparent_temperature"]
humidity = current["relative_humidity_2m"]
wind_speed = current["wind_speed_10m"]
code = current["weather_code"]

# .get() returns a fallback if the code isn't in my table, instead of crashing.
conditions = WEATHER_DESCRIPTIONS.get(code, f"Unknown (code {code})")

# The time comes back as text like "2026-10-21T11:45". Turning it into a
# real datetime lets me print it nicely, e.g. "Wednesday 21 October, 11:45 AM".
observed_at = datetime.fromisoformat(current["time"])

# Now print a clean report. Labels on everything, numbers formatted.
print("=" * 40)
print(f"  Weather report for {CITY}")
print(f"  {observed_at.strftime('%A %d %B %Y, %I:%M %p')}")
print("=" * 40)
print(f"Conditions:   {conditions}")
print(f"Temperature:  {temperature:.1f}°C (feels like {feels_like:.1f}°C)")
print(f"Humidity:     {humidity}%")
print(f"Wind speed:   {wind_speed:.1f} km/h")
print()
print("Next 3 days")
print("-" * 40)

# The daily data is in separate lists (dates, highs, lows, rain chance).
# zip() walks through them together, one day at a time.
for day, high, low, rain in zip(
    daily["time"],
    daily["temperature_2m_max"],
    daily["temperature_2m_min"],
    daily["precipitation_probability_max"],
):
    day_name = datetime.fromisoformat(day).strftime("%a %d %b")
    print(f"{day_name}:  {low:.0f}°C to {high:.0f}°C, {rain}% chance of rain")

print("=" * 40)
