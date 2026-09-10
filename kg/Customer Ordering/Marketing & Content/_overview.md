---
id: 8orders/customer-ordering/marketing-and-content/overview
title: Marketing & Content — Overview
note_type: overview
context: Customer Ordering
feature: Marketing & Content
audience: Business
last_updated: 2026-08-23
tags: [customer-ordering, marketing-and-content, business]
---
# Marketing & Content — Overview

## What is this? (for everyone)

Everything a customer reads in the app that is not a restaurant, a menu or an order: the home-screen
banners, the ads aimed at that particular customer, the app-wide announcement bar, the FAQ, the privacy
policy, the terms, and the "about" counters.

The customer app only **reads** here. Every one of these is written in the back office, in
[[Admin/Catalog & Content Administration/_overview|Catalog & Content Administration]]. So this feature is
one half of a pair, and the half that matters is the agreement between them: what the back office is
allowed to save, and what the app is willing to show. For announcements, those two do not agree — which
is where all of this feature's problems come from.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Home screen | Every customer | Banners and placements for their store type and location |
| 2 | Home screen | Signed-in customer | Ads aimed at them by campaign audience |
| 3 | Announcement bar | Every customer | The current message for their area |
| 4 | Help | Every customer | FAQ |
| 5 | Legal | Every customer | Privacy policy and terms, in their language |
| 6 | About | Every customer | How many store types, items and customers there are |

## Business Flow (plain language)

1. Marketing creates a banner, a campaign or an announcement in the back office.
2. The customer opens the app. It asks for the banners for their location, the ads for them personally,
   and the announcement for their area.
3. Each of those is filtered on the way out: by location, by date range, by day of the week, and by the
   hour window if one was set.
4. Anything the filters exclude simply does not appear. Nothing tells anyone it was excluded.

Point 4 is the one to remember. This feature has no error states of its own — content either shows or
silently does not.

## What a business reader must know

**An announcement can be saved, look correct in the back office, and never appear to a single customer.**
Announcements have an optional "show only between these hours" setting. If that box is ticked but the
times do not save properly, the announcement is stored as active with no times — and the query that
decides what to show requires the times to be there. The result is an announcement that exists, reads as
live, and is invisible. Nothing warns anyone, at any point.

The reason is worth knowing because it is fixable in one place. Banners (`Ads`) and announcements model
exactly the same three settings, and banners **refuse** to be created in that state — the code that
builds a banner rejects "hours enabled with no hours given" outright. Announcements have no such check.
Same three fields, one protected, one not. (#625)

**Saving an ordinary announcement can fail after it has already been sent.** For the most common shape —
a date range with no hour window — the code that schedules the start and end notifications assigns the
same value twice by mistake. The end notification ends up with an empty schedule, which the scheduler
rejects. By that point the announcement is already saved and the push has already gone out, so the admin
sees a failure for something that in fact happened. The natural response is to retry, and because
creating an announcement first switches off any other announcement in the same areas, each retry looks
clean while replacing the previous one. The same mistake exists in the edit screen's code, line for
line. (#623, #627)

**Creating an announcement switches off the others.** Not "replaces the one for the same area" —
switches off *every* active announcement in the areas you selected, or, if you selected none, every
active announcement in the app. That is a real and possibly intended rule, one live announcement at a
time, but nothing states it and nothing tells the person clicking Save. (#627)

**Announcement notification schedules overwrite one another.** The schedules are filed under a name built
from the list of areas, not from the announcement. Two announcements for the same areas share one slot,
every broadcast announcement shares a single slot, and editing an announcement files its schedule under a
*different* name than creation used — so the original keeps running. (#624)

**Editing an announcement can shift the dates.** The create screen and the edit screen interpret the same
date text by different rules. The edit path uses the looser one, which on a server configured for US date
order will read 03/07 as 7 March rather than 3 July, without complaint. (#626)

**The banner endpoint needs no sign-in.** The code that requires a token on the banners controller is
present but commented out, so anyone can fetch the banners for any location. The content is promotional
rather than personal, so the impact is low — but it is one of the twelve endpoints across 8Orders that
are reachable with no credential, and it is in that list for the same reason as the others. (#443)

Finally, two inherited items that show up here: campaign audiences defined as "exactly N days" actually
select everyone within N days, so campaigns reach a larger audience than marketing intends (#423); and
the merchant-facing ad-card list can contain empty entries where the two customer-facing lists put a
placeholder (#437).

## Key Concepts

- **Banner / ad (`Ads`)** — a promotional placement tied to a store type, a city and an area, optionally
  restricted to certain hours, with a separate image per language.
- **Targeted ad (campaign)** — an ad shown only to customers who match an audience defined in the back
  office.
- **Announcement** — the message bar. One per area at a time, optionally limited by date range, weekday
  and hour window.
- **Hour window** — the "show only between these hours" setting shared by banners and announcements. The
  source of most of this feature's findings.
- **Display days** — the weekdays an announcement is allowed to appear on. Empty means every day.
- **Broadcast** — an announcement with no areas selected: it applies app-wide, and switching it on
  switches off every other one.

## Detailed Notes

- [[Customer Ordering/Marketing & Content/_knowledge-graph|Technical Knowledge Graph]] — the endpoint
  index, the read queries, and the announcement authoring path read line by line.
- [[Customer Ordering/Marketing & Content/_scenarios|Scenario Catalog]] — what happens if…
- [[Customer Ordering/Marketing & Content/Notification-Delivery.technical|Notification-Delivery]] — the
  `Ads`, `Announcement` and `AboutApp` entities in detail.
- [[Admin/Catalog & Content Administration/_overview|Catalog & Content Administration]] — where all of
  this content is written.
