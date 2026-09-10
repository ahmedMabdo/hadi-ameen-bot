---
id: 8orders/admin/city-and-geography-administration/overview
title: City & Geography Administration — Overview
note_type: overview
context: Admin
feature: City & Geography Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, city-and-geography-administration, business]
---
# City & Geography Administration — Overview

## What is this? (for everyone)

Where 8Orders decides **where it operates and how each place behaves**.

The geography is a hierarchy: country, city, area, and within a city the delivery zones drivers work
and the restaurant zones that decide which stores serve which addresses. Adding a city is how 8Orders
enters a new market.

But a city is much more than a name on a map. Each one carries its own settings that change how the
platform behaves there: how drivers are scored and paid, how much cash a driver may hold, when the city
pauses for a break, which working days it counts, and — the most operationally significant — what
counts as "too busy".

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Countries | Operations | The top of the hierarchy |
| 2 | Cities | Operations | Add or configure a city |
| 3 | Areas | Operations | Neighbourhoods within a city |
| 4 | Delivery zones | Operations | The geography drivers are assigned within |
| 5 | Restaurant zones | Operations | Which stores serve which areas |
| 6 | Rush-time settings | Operations | When a city is considered overloaded, and how it recovers |
| 7 | Break windows | Operations | Scheduled pauses for a city |
| 8 | City suggestions | Commercial | Places customers asked for that 8Orders does not serve |

## Business Flow (plain language)

1. 8Orders adds a country, then a city, then the areas inside it.
2. Delivery zones and restaurant zones are drawn so drivers can be assigned and stores matched to
   addresses.
3. The city's own settings are configured: driver scoring, payment tiers, cash limits, break windows,
   working days.
4. Rush-time thresholds are set: how many late deliveries mean the city is overloaded, and how far the
   number must fall before things return to normal.
5. In operation, when late deliveries pass the threshold the city enters **rush mode**, which changes
   how deliveries are prioritised. A background check keeps running until the number falls, then rush
   mode ends. An operator can force it to end, but only once the count has actually come down.
6. Requests for places 8Orders does not serve are collected as suggestions.

## What a business reader must know

**Rush mode is the part of this feature with real operational consequence**, and it has one behaviour
worth understanding: the safety checks on the rush-time numbers are applied **only while the city is
not in rush mode**. While a city is actually overloaded — the exact moment those numbers matter — they
can be edited into a state the system would otherwise refuse, for example a "return to normal" figure
higher than the "too busy" figure. Nothing prevents it while rush mode is on.

**Rush mode ends by a job that keeps re-scheduling itself** until the late-delivery count falls. That is
a sensible design, and it means there is no fixed time by which rush mode ends — it ends when conditions
improve. There is no visible limit on how many times it will retry.

**A city is the most connected thing in the platform.** Twenty other parts of the model refer to it.
Changing what a city holds is therefore never a local change: driver pay, driver scoring, cash limits,
pickup-tag numbering and store availability all read from it.

One quality note carried from the city record itself: the same rule — that the driver-scoring weights
must add up to exactly 100% — is enforced with a clean refusal when a city is **created** and by
throwing a raw error when a city is **updated**. Same rule, two different behaviours depending on which
screen you are on.

## Key Concepts

- **Delivery zone** — the area a driver is assigned work within.
- **Restaurant zone** — which stores can serve which areas.
- **Rush mode** — a city-level state meaning "we are overloaded", which changes delivery prioritisation.
- **Busy threshold / reopen-below** — the number of late deliveries that starts rush mode, and the
  lower number that ends it.
- **Break window** — a scheduled pause for a whole city.
- **Working day** — counted per city, and the basis of the daily pickup-tag sequence.
- **City suggestion** — demand recorded for a place 8Orders does not yet serve.

## Detailed Notes

- [[Admin/City & Geography Administration/_knowledge-graph|Technical Knowledge Graph]] — every rush-mode
  rule with its guard, and the three-component lifecycle.
- [[Admin/City & Geography Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[City.business|City]] · [[CityRushTimeConfiguration.business|City Rush Time Configuration]] ·
  [[Area-and-Country|Area & Country]] · [[CityBreakConfiguration|City Break Configuration]]
