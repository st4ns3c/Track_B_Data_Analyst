# Changelog

## v1.0: client delivery (Week 2 · Day 8)

Packaged from the [Week 1 · Day 5 original](../../../Week1_APIS/Day5/weather_dashboard/). The original stays as it was.

**Changed**
- README: added an **Assumptions** section (local use, metric units, free-plan limits, what "3-day forecast" means, which city wins when names clash, local times)
- README: the setup path and version line now point to this delivered copy
- Added this changelog

**Checked, no change needed**
- `index.html` has no commented-out code and no debug statements (`console.log`, `debugger`, `DEBUG`, `TODO`, `FIXME`)
- The API keys are only in `config.js`, which is in `.gitignore`. Only `config.example.js` (placeholders) is committed
- Run from a clean state (a fresh clone plus `config.js`): the Nairobi search loads the weather, the country card and the 3-day forecast
