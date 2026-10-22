# Week 1 · Day 5: Projects

Three small, complete projects that close out Week 1 (APIs). Each folder has its own README with setup, usage and a real example output.

| Project | What it does | Built with | API key needed? |
|---|---|---|---|
| [Sales Data Reader](sales_data_reader/) | Reads a sales CSV and reports total sales, the top salesperson and sales per county | Python, `csv` | None |
| [Kenyan Business Currency Tracker](currency_tracker/) | Converts a KES price into USD, EUR and GBP at today's live rates | Python, ExchangeRate-API | Optional |
| [City Weather Dashboard](weather_dashboard/) | One web page with current weather, a 3-day forecast and country facts for any city | HTML/JavaScript, OpenWeatherMap, REST Countries | Yes (two free keys) |

## Pre-push checklist (from the Day 5 notes)

- [x] Each project runs from a fresh terminal with no errors
- [x] Tested with at least 3 different inputs
- [x] Tested bad inputs (city that doesn't exist, bad API key, broken CSV rows, non-numeric prices)
- [x] `.env` and `config.js` are in `.gitignore` and not in git
- [x] No hardcoded API keys in any file
- [x] Every README has setup instructions and output from an actual run
- [x] No commented-out code or leftover debug prints
