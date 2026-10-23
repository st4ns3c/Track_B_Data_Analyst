# Day 8: Delivering Work Professionally

*Week 2 · Client Cycle · Exercise: build a complete delivery package for a Phase I project, as if handing it to a paying client.*

**Project delivered:** the City Weather Dashboard from Week 1 · Day 5. It was copied into [`weather_dashboard/`](weather_dashboard/) and packaged here, so the [original](../../Week1_APIS/Day5/weather_dashboard/) stays untouched and the git history shows exactly what changed for delivery (see [CHANGELOG.md](weather_dashboard/CHANGELOG.md)).
**Delivered version:** git tag `weather-dashboard-v1.0`

## The scenario

A small travel company asked for one page where staff can type a client's destination and see the weather now, the next few days, and the country basics, without opening three websites. The agreed scope was:

1. Current weather for any city
2. A 3-day forecast
3. Country facts: capital, population, currency, languages, flag
4. Clear error messages, not a broken page
5. A setup guide their team can follow

## The four parts of the delivery package

| Part | Where | Status |
|---|---|---|
| **1. Clean code** | [`weather_dashboard/index.html`](weather_dashboard/index.html) | Checked: no commented-out code, no debug prints, and keys in `config.js`, not in the code |
| **2. README** | [`weather_dashboard/README.md`](weather_dashboard/README.md) | Updated: added an **Assumptions** section, the delivered version and a [CHANGELOG](weather_dashboard/CHANGELOG.md) |
| **3. Delivery message** | [`delivery_message.md`](delivery_message.md) | Written |
| **4. Written sign-off** | The client's reply to the delivery message | The message asks for written confirmation before the final 50% is invoiced. Silence doesn't count |

## Pre-delivery checklist (from the Day 8 notes)

| Check | Result |
|---|---|
| Delete commented-out code | None found. Every comment explains *why* the code does something; none are switched-off code |
| Remove debug statements | `grep` for `console.log`, `debugger`, `DEBUG`, `TODO`, `FIXME` found nothing |
| Sensitive values in a config file that's in `.gitignore` | The keys are in `config.js`, which is listed in `weather_dashboard/.gitignore`. A fresh clone from GitHub has **no** `config.js` |
| README up to date | Setup, usage, the three states, error handling and files are current. **Assumptions** added (units, free-plan limits, local server, local time, which city wins when names clash) |
| Run from a clean state | Cloned fresh from GitHub, added `config.js`, served it and searched for **Nairobi**. Result below |
| Tag the release | `git tag weather-dashboard-v1.0` and `git push --tags` |

**Clean-state run (fresh clone, 23 Oct 2026):**

```
Nairobi, KE   Friday 8:46 pm local time
24°C  Broken clouds  ·  23°C feels like  ·  47% humidity  ·  23 km/h wind

About the country: Kenya (Republic of Kenya)
Capital Nairobi · Region Eastern Africa · Population 54,227,015
Currency Kenyan shilling (KES) · Languages English, Swahili · Dialling code +254 · Cars drive on the left

Next 3 days
Sat 24 Oct  29° / 18°  Light rain       💧 40% chance of rain
Sun 25 Oct  30° / 16°  Overcast clouds  💧 0% chance of rain
Mon 26 Oct  29° / 16°  Overcast clouds  💧 36% chance of rain
```

### Why the tag is `weather-dashboard-v1.0` and not `v1.0`

This repo holds many projects (one per day of the course). A plain `v1.0` would point at the whole repo and couldn't tell you *which* project was delivered. Naming the tag after the project means the client, or future me, can always come back to exactly the code that was handed over, even after later commits.

## Revision vs new feature

**A revision** is when the 3-day forecast shows the wrong day names for a city in another time zone, or the country card stays empty for a valid city. That's in the agreed scope, so I fix it free and the same week. **A new feature** is a request like "save our favourite cities", "add an hourly rain chart", or "send us an SMS when rain is forecast". None of those were in the brief, so I quote them separately.

How I'd reply to a feature request:

> That's a great idea, and it would fit well with what's already built. Saving favourite cities is outside the original brief, so I'd quote it separately. I can scope it and send you a price if you want to go ahead. Everything in the original brief is working as agreed, so it's ready for your sign-off whenever you are.

And for any request, the same-day acknowledgement:

> Received, thank you. I'm looking at it now and will get back to you by end of day.

## Files

| File | What it is |
|---|---|
| `README.md` | This page: the delivery package, checklist, and revision vs feature |
| `weather_dashboard/` | The delivered copy of the dashboard (code, README, CHANGELOG) |
| `delivery_message.md` | The message sent to the client with the delivery |
