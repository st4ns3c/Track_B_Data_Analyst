# Day 25: Project, Interactive Dashboard

*Week 5 · Dashboards and Reporting · Last day of the week. One project, one exercise, both deployed to Streamlit Cloud.*

Four days of dashboard skills, then two dashboards a client can open in a browser. Each folder is independent, with its own data generator, app, sample data, requirements and README.

## What is here

| Folder | What it is | Live link |
|---|---|---|
| [`project/`](project/README.md) | **The project.** Sales Performance Dashboard for Otieno Wholesale Supplies, a Nairobi distributor: 52 shops, five counties, June to November 2026 | [Open the dashboard](https://otieno-wholesale-dashboard.streamlit.app/) |
| [`exercise/`](exercise/README.md) | **The exercise.** M-Pesa Business Tracker: upload a business statement and see daily sales, transaction types, weekly trend and busiest hours | [Open the tracker](https://mpesa-business1-tracker.streamlit.app/) |

## The project in one paragraph

County and month filters, four headline numbers with month-on-month change, a revenue trend, the top ten accounts, and the shops that have stopped ordering. In the sample, **11 shops have gone quiet for 30 days or more, and together they used to bring in about KES 1.93M a month.** The page ranks them by what each was worth and gives the owner a call list to download.

```bash
cd project && streamlit run app.py
```

## The exercise in one paragraph

Option 1 of the three: **the M-Pesa Business Tracker**, the one I can sell soonest. It reads a business statement CSV, the owner's own upload or a sample cafe statement. It counts only completed payments, takes reversals off sales, and keeps money moved to the bank out of spending. In the sample: **KES 2.24M in sales from 6,087 payments, busiest at 1 pm**. Setup is priced at KES 18,000.

```bash
cd exercise && streamlit run app.py
```

## Deploying to Streamlit Cloud

Both apps are ready to deploy straight from this repository. Each folder has its own `requirements.txt` (Streamlit looks next to the app file first) and its own committed sample CSV, and every path in the code is built from the app's own folder.

**For each app:**

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub as **st4ns3c**. The first time, allow Streamlit to read your repositories.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:

   | Field | Project | Exercise |
   |---|---|---|
   | Repository | `st4ns3c/Track_B_Data_Analyst` | `st4ns3c/Track_B_Data_Analyst` |
   | Branch | `main` | `main` |
   | Main file path | `Week5_DashboardsandReporting/Day25/project/app.py` | `Week5_DashboardsandReporting/Day25/exercise/app.py` |
   | App URL (your choice) | for example `otieno-wholesale-dashboard` | for example `mpesa-business-tracker` |

4. Open **Advanced settings** and choose **Python 3.13** (or the newest offered; it must be 3.11 or later for pandas 3).
5. Click **Deploy**. The first build takes a few minutes while it installs the requirements.
6. When it loads, check:
   - the four headline numbers and all the charts appear
   - the filters change the page
   - the M-Pesa tracker accepts an upload (any CSV with the right columns)

If the build fails, the log on the right of the deploy screen says why. The most likely cause is a pinned version not being available for the chosen Python. Copy the last red lines of the log and I'll adjust `requirements.txt`.

**Deployed:** both apps are live on Streamlit Cloud, from `main`: the [project](https://otieno-wholesale-dashboard.streamlit.app/) and the [exercise](https://mpesa-business1-tracker.streamlit.app/). Each one updates by itself when changes are pushed to `main`.

## Tags

The repository already has a `v1.0` tag (from an earlier project), so these releases get named tags, like the earlier `database-analysis-v1.0`:

| Tag | Release |
|---|---|
| `distributor-dashboard-v1.0` | The project, once its live URL is in the README |
| `mpesa-tracker-v1.0` | The exercise, once its live URL is in the README |

## Sharing

The brief asks for the M-Pesa tracker link to be posted in the Amerix WhatsApp channel, so others can try the filters and suggest what to add. Their suggestions are the start of a version 1.1.

## What the week covered, and where it shows up

| Day | Topic | Where it appears in Day 25 |
|---|---|---|
| 21 | Building with Streamlit: metrics, charts, a date slider | Both: `st.metric` cards, Altair charts, cached loading |
| 22 | Advanced components: dropdowns, date pickers, uploads, downloads | Project: county and month dropdowns, call-list download. Exercise: statement upload, date range, type filter, CSV download |
| 23 | Data storytelling | Both: a description first, captions that say what a chart means, emphasis colour |
| 24 | Automated reports | Both: "data up to" and statement dates on the page, so the reader knows how fresh it is |
| 25 | A deployed, client-ready dashboard | Both, end to end |

## Note on the data

Both datasets are **synthetic**, written by generators with fixed seeds (25 for the project, 2525 for the exercise), and both businesses are fictional. Unlike earlier days, the sample CSVs **are** committed, because the deployed apps read them.
