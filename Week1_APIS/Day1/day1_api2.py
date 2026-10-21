import os
import requests

# REST Countries now requires an API key (see Docs/APIS.md notes).
# Set it in your terminal first:  export RESTCOUNTRIES_API_KEY="your_key_here"
api_key = os.environ.get("RESTCOUNTRIES_API_KEY", "rc_live_demo")

url = "https://api.restcountries.com/countries/v5?names.common=kenya"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()["data"]

    if "_demo" in data:
        print("NOTE: using the demo key, so this is sample data, not your search.")
        print("Get a free key at https://restcountries.com/sign-up\n")

    country = data["objects"][0]

    name = country["names"]["common"]
    capital = country["capitals"][0]["name"]
    population = country["population"]
    currency = country["currencies"][0]["code"]

    print(f"Country: {name}")
    print(f"Capital: {capital}")
    print(f"Population: {population:,}")
    print(f"Currency: {currency}")
else:
    print("Request failed. Status:", response.status_code)
    print(response.json())
