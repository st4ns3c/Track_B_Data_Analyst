import os
import requests

# REST Countries now requires an API key (see Docs/APIS.md notes).
# Set it in your terminal first:  export RESTCOUNTRIES_API_KEY="your_key_here"
api_key = os.environ.get("RESTCOUNTRIES_API_KEY", "rc_live_demo")

url = "https://api.restcountries.com/countries/v5?q=kenya"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(url, headers=headers)

print("Status code:", response.status_code)
print("Data received:", response.json())
