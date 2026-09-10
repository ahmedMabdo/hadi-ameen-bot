---
id: 8orders/customer-ordering/tiered-discount/overview
title: Tiered Discount — Overview
note_type: overview
context: Customer Ordering
feature: Tiered Discount
audience: Business
last_updated: 2026-08-02
---
# Tiered Discount — Overview

## What is this? (for everyone)
Tiered Discount is a "spend more, save more" promotion tool. Ops staff sets up a campaign with one
to three spending thresholds, each unlocking a bigger reward than the last — for example, spend 200
EGP and get 10% off, spend 400 EGP and get 15% off. A campaign can apply to the whole order or just
the delivery fee, and can be aimed at everyone, specific customers, a customer segment, or one or a
few restaurants.

The cost of the discount doesn't come entirely out of 8Order's pocket or the restaurant's — it's
split between them at a percentage agreed when the campaign is created, and that split always has
to add up to 100%.

Since guest browsing launched, a campaign can also be marked visible to guests — people who haven't
logged in yet — so a promotion can hook someone before they've even created an account. If a guest
locks in a discount on their cart and then logs in, they keep that exact discount rather than having
it re-checked against their now-real account.

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Tiered Discount list/create/edit (Admin back-office) | Ops / Admin | Set up a campaign: name, tiers, cost split, date window, targeting |
| 2 | Restaurant/cart view (Customer mobile app) | Customer or Guest | See the "spend X more to unlock Y% off" progress banner |
| 3 | Checkout | Customer or Guest | The best-matching discount is automatically applied to the order or delivery fee |
| 4 | Tiered Discount list (Admin back-office) | Ops / Admin | Activate, deactivate, edit, or delete a campaign |

## Business Flow (plain language)
1. Ops creates a campaign in the Admin back-office: name, one to three spend/reward tiers, whether
   it's a percentage or fixed amount, the merchant/customer/segment targeting, the date window, and
   the restaurant/8Order cost split.
2. While a customer (or guest) browses a participating restaurant and builds up their cart, the app
   shows how much more they need to spend to reach the next reward tier.
3. At checkout, the system finds the single best-matching, currently-valid campaign for that
   customer and restaurant, and applies its discount — capped at the campaign's maximum discount
   value, and never exceeding the order or delivery fee itself.
4. If the restaurant is already running its own item-level offer, the tiered discount is suppressed
   unless the campaign was explicitly set up to allow stacking with one.
5. If a guest had a discount locked to their cart, that discount survives them logging in — it isn't
   re-evaluated against their real account.
6. Ops can pause (deactivate), resume (reactivate — blocked if the campaign has already expired),
   edit, or remove a campaign at any time from the Admin back-office.

## Key Concepts
- **Tier** — one spend threshold + its reward. A campaign has 1–3 of these, each strictly bigger
  than the last in both threshold and reward.
- **Merchant / 8Order contribution** — how the discount's cost is split between the restaurant and
  8Order; always adds up to 100%.
- **Available to guests** — a per-campaign setting controlling whether a not-yet-logged-in shopper
  can see and use the discount.
- **Guest Mode discount lock** — see the Customer Ordering context's own
  [[../../../../Talabatk.IDS/CONTEXT|CONTEXT.md]] for the full Guest Mode picture; this feature's
  role in it is that a discount a guest locked in survives their login.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — for developers & CR work.
- [[_scenarios|Scenario Catalog]] — what happens in each case, and what's already covered.
