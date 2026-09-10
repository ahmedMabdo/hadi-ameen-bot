---
id: 8orders/customer-ordering/order-and-fulfilment/overview
title: Order & Fulfilment — Overview
note_type: overview
context: Customer Ordering
feature: Order & Fulfilment
audience: Business
last_updated: 2026-08-02
---
# Order & Fulfilment — Overview

## What is this? (for everyone)
This covers what happens the moment a checkout succeeds: an Order is created, paid for, and
(depending on risk signals) may need a manual review step before the restaurant even sees it. From
there, restaurants, delivery staff, and admin all work the same order record toward delivery — this
note focuses on what the **customer** experiences: payment, the review gate, cancellation, and (for
multi-restaurant orders) the per-restaurant pickup tracking number.

**Scope note:** `Order` is the single largest, most central entity in the whole codebase (over
6,000 lines), touched by every part of the business. This documentation pass only covers the
customer-facing slice — the restaurant-confirmation, delivery-assignment, and admin/compensation
slices are intentionally left for when those areas get their own knowledge-graph pass.

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Checkout | Customer | Order created from the cart |
| 2 | (conditional) Pending review | — | Riskier orders wait for manual/system review before the restaurant sees them |
| 3 | Order tracking | Customer | Follow status as the restaurant/delivery side progresses it |
| 4 | Order history / cancel | Customer | Cancel while still possible; view past orders |

## Business Flow (plain language)
1. Checkout succeeds → an Order is created with a payment split (cash/wallet/online, cash and
   online never combined) and any discounts already resolved into fixed amounts.
2. Most repeat-customer, single-restaurant, cash orders below a size threshold go straight to the
   restaurant. First orders, online/Apple Pay orders, multi-restaurant orders, duplicate open
   orders at the same restaurant, or unusually large orders get an extra review step first.
3. If an order spans multiple restaurants, each restaurant gets its own short pickup number (the
   Daily Pickup Tag, already documented in this context's `CONTEXT.md`) so a merchant/driver can
   identify their portion without the full order code.
4. The customer can cancel their own order — but only until the restaurant has confirmed it.

## Key Concepts
- **Pending vs. Restaurant Pending** — the two possible starting states, one gated by risk signals,
  one going straight through.
- **Portion** — one restaurant's slice of a multi-merchant order, each with its own status and
  discount attribution.
- **Daily Pickup Tag** — see `CONTEXT.md`, already fully documented there.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — for developers & CR work, with an explicit scope
  boundary on what's and isn't covered.
- [[_scenarios|Scenario Catalog]]
