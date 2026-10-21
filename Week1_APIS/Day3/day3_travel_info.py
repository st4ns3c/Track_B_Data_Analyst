#The user enters a city, and the tool tells them the weather plus basic country information about that city's country.
# Each API call is its own function. If the weather API changes, you update get_weather(). 
# The rest of the tool does not change. Keep your API calls in functions from the start.
"""
Travel Weather Tool
-------------------
Shows weather and country information for any city.

Usage:
    python day3_travel_info.py

Requirements:
    pip install requests python-dotenv
    OPENWEATHER_API_KEY in .env file
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENWEATHER_API_KEY")
countries_api_key = os.getenv("RESTCOUNTRIES_API_KEY")


def get_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None


# REST Countries shut down /v3.1. The new /v5 needs a key, and wraps the
# results in {"data": {"objects": [...]}} instead of returning a plain list.
def get_country_info(country_code):
    url = f"https://api.restcountries.com/countries/v5/codes.alpha_2/{country_code}"
    headers = {"Authorization": f"Bearer {countries_api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        countries = response.json()["data"]["objects"]
        if countries:
            return countries[0]
    return None


def run_tool():
    print("Travel Weather Tool")
    print("-------------------")
    city = input("Enter a city name: ").strip()

    if not city:
        print("No city entered. Exiting.")
        return

    print(f"\nFetching data for {city}...")

    weather_data = get_weather(city)

    if not weather_data:
        print(f"Could not find weather data for '{city}'. Check the city name and try again.")
        return

    country_code = weather_data["sys"]["country"]
    country_data = get_country_info(country_code)

    print(f"\n=== {city.title()}, {country_code} ===")
    print(f"Temperature : {weather_data['main']['temp']}C")
    print(f"Condition   : {weather_data['weather'][0]['description'].title()}")
    print(f"Humidity    : {weather_data['main']['humidity']}%")
    print(f"Wind        : {weather_data['wind']['speed']} m/s")

    if country_data:
        population = country_data.get("population", 0)
        region = country_data.get("region", "Unknown")
        # v5 gives a list like [{"code": "KES", "name": "Kenyan shilling", ...}]
        currencies = ", ".join(c["code"] for c in country_data.get("currencies", []))
        print(f"\n=== Country Info ===")
        print(f"Region      : {region}")
        print(f"Population  : {population:,}")
        print(f"Currency    : {currencies}")


run_tool()