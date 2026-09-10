---
id: 8orders/customer-ordering/customer-account/overview
title: Customer Account — Overview
note_type: overview
context: Customer Ordering
feature: Customer Account
audience: Business
last_updated: 2026-08-02
---
# Customer Account — Overview

## What is this? (for everyone)
Everything about managing a customer's own profile: personal info, saved addresses, saved cards,
device registrations (for push notifications), language, notification settings, in-app
notifications, and loyalty points — including redeeming points into a Voucher (see
[[Customer Ordering/Discounts & Coupons/_overview|Discounts & Coupons]] for what a Voucher does once
created). It also covers a separate, unrelated integration: crediting a customer's wallet from an
external recycling-rewards partner ("I Recycle").

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Profile | Customer | View/update personal info, saved cards, addresses |
| 2 | Loyalty points | Customer | View points, history, redeem into a Voucher |
| 3 | Notifications | Customer | View/manage in-app notifications and notification settings |
| 4 | Settings | Customer | Preferred language, device registration |

## Business Flow (plain language)
1. A customer manages their own profile, addresses, and cards directly.
2. Loyalty points accumulate from ordering activity (earning side not covered in this pass) and can
   be redeemed — either generally or against a specific participating merchant — into a Voucher.
3. Separately, an external recycling-rewards partner can credit a customer's wallet directly by
   phone number, entirely outside the loyalty-points system.

## Key Concepts
- **Loyalty points redemption** — the actual source of a [[Customer Ordering/Discounts & Coupons/_overview|Voucher]] (corrects an earlier guess in this knowledge graph that pointed at the wrong controller).
- **I Recycle wallet credit** — an external, unrelated integration; not part of the loyalty program.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — includes a flagged bug: the User Preferences
  feature currently always returns empty, regardless of its feature flag.
