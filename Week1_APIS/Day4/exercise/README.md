# City Weather (Fetch API in the browser)

A single web page that shows live weather for any city in the world: conditions right now plus a 5-day forecast. Everything happens in the browser with JavaScript's `fetch()`. There's no Python, no server and no API key.

*Week 1 · Day 4 exercise: Fetch API in JavaScript.*

## How to run it

Double-click `weather.html` (or drag it into Chrome/Firefox). That's it.

Type a city and press **Search** (or Enter), or click one of the quick-pick towns.

## What it does

The page makes two API calls, and the result of the first one feeds the second:

```
City name ("Mombasa")
  └─> 1. Open-Meteo Geocoding API  ──> latitude, longitude, country
        └─> 2. Open-Meteo Forecast API ──> current weather + 5-day forecast
              └─> shown as a weather card on the page
```

Open-Meteo's weather API only accepts coordinates, which is why the city name is looked up first.

## The three states

The result box is always in exactly one of these states, so the page never looks frozen or broken:

| State | When | What you see |
|---|---|---|
| **Loading** | Straight after you search, before the first `await` | Blue italic `Loading weather for Tokyo...`, and the Search button is greyed out so it can't be double-clicked |
| **Success** | Both API calls worked | City, local time, temperature, conditions, feels like, humidity, wind, and a 5-day forecast with rain chances |
| **Error** | Anything went wrong | A red box explaining what happened in plain English |

## How errors are handled

| Situation | Message |
|---|---|
| Empty search box | `Please enter a city name first.` |
| City doesn't exist / misspelled | `No city called "Xyzqwe" was found. Check the spelling and try again.` |
| No internet / request blocked | `Couldn't reach the city search service. Check your internet connection.` |
| Too many requests (429) | `Too many weather requests. Wait a minute and try again.` |
| Server problem (500+) | `The weather service is having problems right now (503). Try again later.` |
| Any other bad status | `The weather request failed (status 400).` |

One catch I had to deal with: when a city doesn't exist, the geocoding API still answers **200 OK**, but without a `results` list. So checking `response.ok` isn't enough. The code also checks that results came back.

## Why Open-Meteo (and not the lesson's REST Countries example)?

- **No API key.** Anything in browser JavaScript can be seen by anyone with "View Page Source", so a key would leak. Open-Meteo doesn't need one.
- **It allows browser requests.** It sends `Access-Control-Allow-Origin: *`, so it works even when the file is opened straight from your computer.
- **REST Countries v3.1 (used in the lesson's `day4_fetch.html`) has been shut down.** The new v5 needs a key and rejects requests from pages it hasn't been told to trust. That's exactly the kind of API that belongs behind your own backend (the pattern for Day 16), not in browser code.

## Files

| File | What it is |
|---|---|
| `weather.html` | The whole app: HTML, CSS and JavaScript in one file |
| `README.md` | This guide |

## What I practised

- `fetch()` with `async`/`await`, including the second `await` for `response.json()`
- `try`/`catch`, and throwing my own errors with clear messages
- Checking `response.ok`, plus checking the data itself
- Chaining two API calls (geocoding → forecast)
- Building the URL safely with `encodeURIComponent` and `URLSearchParams`
- Updating the page with DOM manipulation (`innerHTML`, `textContent`, `className`)
- Escaping user input before putting it in `innerHTML`, so typed HTML can't run
- A loading state, plus disabling the button while waiting
