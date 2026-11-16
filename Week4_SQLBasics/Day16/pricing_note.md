# Pricing note: Monday morning reporting setup

**Client:** Nairobi wholesale distributor
**Scope:** one SQLite orders database, the five Monday-morning queries, and the script that prints them
**Quote date:** 16 November 2026
**Currency:** Kenyan shillings, exclusive of VAT
**Validity:** 30 days

The price is split into a one-off build and a monthly support fee. The client owns the database and the scripts after handover; the monthly fee keeps them working as the order book changes.

## Setup: KES 35,000 one-time

| Work | Hours |
|---|---:|
| Requirements and review of the current Excel routine | 3 |
| Database design, import and cleaning of the order data | 5 |
| Write and test the five queries, including the calculated order value | 6 |
| Handover: README, one training session and 30 days of bug fixes | 6 |
| **Total** | **20** |

At KES 1,750 per hour, 20 hours is **KES 35,000**. The client receives:

- `data/orders.db` with the `orders` table and the historical rows
- `generate_orders.py`, which rebuilds the sample database cleanly
- `queries.py`, which prints all five answers in one run
- a short README covering how to run it and what each answer means
- one handover session, on site or online
- 30 days of fixes for anything that does not work as described

## Monthly support: KES 9,000 per month

| Included each month | Detail |
|---|---|
| Up to 4 hours of support | Data checks, small query changes, help when a result looks wrong |
| Two small report changes | For example, a new county filter or an extra column |
| One monthly health check | Confirm the database opens, the row count is sensible and the five queries still run |
| Backup copy | A dated copy of the database kept for 30 days |
| Response time | Within two business days |

Four hours at KES 2,250 per hour is KES 9,000. A 12-month prepayment is **KES 97,200**, a 10% discount on KES 108,000.

There is no lock-in: the client can stop the support and keep using the database and scripts as they are.

## Optional extras

| Item | Price |
|---|---:|
| Additional report beyond the two included changes | KES 3,000 each |
| Additional data source or county file added to the monthly import | KES 8,000 one-time |
| Same-day or weekend support | KES 3,000 per hour |
| Web dashboard on top of the database | From KES 90,000, quoted separately |
| Extra training session | KES 7,000 per session |

## What the price assumes

- The client supplies orders as CSV or Excel with consistent column names, or gives access to the current export.
- The database stays on one office computer or one shared drive. This is not a multi-user server.
- SQLite is sufficient: one writer at a time, and well under a million rows a year. If the order book grows past that, a PostgreSQL move is a separate project.
- The five questions are the scope. New analysis is quoted as an extra, not absorbed into support.
- The client names one person who can approve changes and attend handover.
- Travel outside Nairobi is charged at cost.

## Why this structure

The manual routine takes about 45 minutes a week, or roughly 39 hours a year. At a modest KES 1,500 per hour of manager time, that is about KES 58,500 of time that can go back into selling. The setup pays for itself in around seven months on that measure alone, before counting the errors the manual copy-and-paste routine can introduce.

The monthly fee is deliberately separate so the client can see the difference between **building** the report and **keeping** it correct. The build is a fixed package, not an open-ended hourly bill. Support is capped at four hours so both sides know the ceiling; work beyond that is agreed first.

## Payment terms

- 50% deposit on acceptance, 50% on handover.
- Monthly support billed on the first working day of the month.
- Invoices payable within 14 days.
- Prices held for 12 months, then reviewed with the client.

---

*Prepared for the Day 16 exercise. The figures are a reasoned quote for this scope, not a market survey.*
