import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENWEATHER_API_KEY")
city = "London"  # You can change this to any city you want

url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    temp = data["main"]["temp"]
    description = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]

    print(f"Weather in {city}")
    print(f"Temperature: {temp}C")
    print(f"Condition: {description}")
    print(f"Humidity: {humidity}%")
else:
    print(f"Error: {response.status_code} - {response.text}")