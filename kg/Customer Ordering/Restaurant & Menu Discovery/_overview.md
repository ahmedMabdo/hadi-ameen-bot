---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/overview
title: Restaurant & Menu Discovery — Overview
note_type: overview
context: Customer Ordering
feature: Restaurant & Menu Discovery
audience: Business
last_updated: 2026-08-02
---
# Restaurant & Menu Discovery — Overview

## What is this? (for everyone)
Everything about finding a restaurant or Mart (grocery store) and browsing its menu. A Mart isn't a
different kind of thing in the system — it's the same "Restaurant" record, just flagged as a store,
browsed through mart-specific categories and search instead of a menu.

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Home page | Customer | See featured restaurants/marts, banners, sliders |
| 2 | Search | Customer | Find a restaurant, mart, or item by name/category |
| 3 | Restaurant/Mart page | Customer | Browse the menu, see open/closed status |
| 4 | Favourites | Customer | Save restaurants for quick access later |

## Business Flow (plain language)
1. A customer finds a restaurant or mart via the home page, search, or their favourites.
2. Whether it shows as open depends on its working-hours schedule for right now, including
   overnight hours.
3. Items on the menu can be temporarily unavailable — sometimes because the restaurant marked them
   out for an hour or two, sometimes because they've been rejected from orders repeatedly and are
   in an escalating cool-down, and for Mart items, because they're out of stock.
4. A customer can subscribe to be notified when an out-of-stock Mart item is back.

## Key Concepts
- **Mart = Restaurant, `IsStore=true`** — not a separate concept.
- **Availability vs. Active** — availability is temporary/reason-coded; `Active=false` is a full
  deactivation.
- **Escalating unavailability** — repeated order rejections on the same item double its cool-down
  period each time.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]]
