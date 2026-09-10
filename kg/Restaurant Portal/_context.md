---
id: 8orders/restaurant-portal/context
note_type: context
context: Restaurant Portal
last_updated: 2026-08-23
tags: [context, restaurant-portal]
---
# Restaurant Portal — Overview

Merchant-facing portal for managing menus and incoming orders (`TalabatkRestaurants`, Angular SPA).

> No `CONTEXT.md` exists yet for this context (per `CONTEXT-MAP.md`) — still an Open Question.
> `Restaurant`/`MenuItem` browsing-slice entities are already documented under
> [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph|Customer Ordering/Restaurant & Menu Discovery]];
> this hub covers the **management** side those notes explicitly excluded.

## Features
- [[Restaurant Portal/Menu & Order Management/_knowledge-graph|Menu & Order Management]] — controller inventory; 3
  confirmed findings (StoresHub dead-code bug, `Restaurant.UpdateRestaurant` unreachable from this
  host, duplicate feature-flag endpoints)

## Integrates With
- [[Customer Ordering/_context|Customer Ordering]] — receives new-order push notifications
  (`ApiClientHandler` → `StoresHub` SignalR, `/operationHub`)
- <see [[_integrations|integration register]] for details>
