---
id: 8orders/restaurant-portal/merchant-finance-and-reporting/overview
title: Merchant Finance & Reporting — Overview
note_type: overview
context: Restaurant Portal
feature: Merchant Finance & Reporting
audience: Business
last_updated: 2026-08-23
tags: [restaurant-portal, merchant-finance-and-reporting, business]
---
# Merchant Finance & Reporting — Overview

## What is this? (for everyone)

This is the part of the Restaurant Portal where a restaurant finds out **how much money it has earned
and how well it is doing**. It answers the questions a restaurant owner actually asks: what is my
balance, when was I last paid, which items sell, how many orders did my staff reject, and how long
are customers waiting.

It has three groups of screens. **Money**: the current balance, the history of payments 8Orders has
made to the store, and the orders behind each one. **Reports**: sales by item, rejected orders, menu
activity, a daily and a total statement, and a financial summary — all rendered by a reporting engine
that can also export to PDF and Excel. **Dashboard**: five charts that turn the same data into trends
— unavailable time, preparation time, avoidable waiting, customer cancellations, and rejection rate.

Two extra jobs live here because they belong to the same office rather than the kitchen: bulk menu
editing through Excel (export the menu, change prices in a spreadsheet, upload it back) and reserving
advertising slots inside the customer app.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Balance | Merchant admin, Restaurant admin | What 8Orders currently owes the store |
| 2 | Payments history | Merchant admin, Restaurant admin | Every settlement paid out, and the orders behind it |
| 3 | Daily / total statement | Merchant admin, Restaurant admin | Period statements for accounting |
| 4 | Financial summary | Merchant admin, Restaurant admin | One-page money view for a date range |
| 5 | Sales & item reports | Merchant admin, Restaurant admin | Which items sold, which sat unavailable, turnover rate |
| 6 | Rejected orders report | Merchant admin, Restaurant admin | What was rejected and why — the number 8Orders judges them on |
| 7 | Dashboard | Merchant admin, Restaurant admin | Five performance charts over time |
| 8 | Excel menu import/export | Merchant admin, data entry | Change many prices or items at once |
| 9 | Ad slots | Merchant admin, Restaurant admin | Browse and reserve promotional placements |

## Business Flow (plain language)

1. A customer's order completes. Its value, 8Orders' commission and the delivery cost are turned into
   settlement lines against the restaurant.
2. Those lines accumulate into a balance the merchant can see, and into the payment history once
   8Orders settles.
3. The same order data is aggregated into the reports and the dashboard charts.
4. Separately, the same settlement lines are batched every day into 8Orders' accounting system
   (AccFlex) — the restaurant never sees that step, but it is the same source of truth.
5. When a merchant needs to change many menu prices, they export the menu, edit the spreadsheet,
   preview the change, and confirm it.

## What a business reader should know about trust in these numbers

The figures themselves come from real order data, so a merchant looking at **their own** store sees
the truth. The caveat is about *whose* store the screens can be made to show.

Twelve recorded findings sit in this feature. The pattern is the same in nearly all of them: the
screen sends a restaurant number to the server, and for several reports the server uses the number it
was given rather than the one attached to the signed-in user. In practice a signed-in merchant who
edits that number can read another restaurant's daily statement, financial summary, or dashboard
charts, and can reserve advertising slots in another restaurant's name.

Three of the newest reports do it correctly and are worth calling out as the pattern to copy: they
check the requested store against the list the signed-in user is allowed to see, and return nothing if
it is not on the list. Notably they return an **empty report** rather than an error, which looks
identical to "no sales in this period" — so absence of data is not evidence of correct access.

Two more findings are about reach rather than tenancy: one file-upload endpoint accepts uploads with
**no sign-in at all**, and the reporting engine's designer and viewer pages are not behind a login.

All of this is recorded, not fixed — the register rows are #42, #437, #570, #571, #580, #582, #583,
#584, #593, #603 and IDOR #9. The technical note lists each endpoint with a verdict.

## Key Concepts

- **Balance** — money 8Orders owes the store right now, from unsettled statement lines.
- **Settlement line** — one accounting entry generated from an order (value, commission, delivery
  cost); the atom behind every figure here.
- **Statement** — a period view of settlement lines: daily detail or a total.
- **Rejection rate** — share of incoming orders the store refused; drives the store's KPI score.
- **Avoidable wait** — waiting time the report attributes to the store rather than to the driver or
  the customer.
- **Ad card / reserved ad** — a promotional slot in the customer app that a store books for a period.

## Detailed Notes

- [[Restaurant Portal/Merchant Finance & Reporting/_knowledge-graph|Technical Knowledge Graph]] — the
  endpoint-by-endpoint scoping verdicts and the three scoping patterns.
- [[Restaurant Portal/Merchant Finance & Reporting/_scenarios|Scenario Catalog]] — what happens if…
- [[Restaurant Portal/Merchant Account & Access/_overview|Merchant Account & Access]] — who is
  allowed to see which store.
