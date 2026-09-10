---
id: 8orders/customer-ordering/cart-and-checkout/overview
title: Cart & Checkout — Overview
note_type: overview
context: Customer Ordering
feature: Cart & Checkout
audience: Business
last_updated: 2026-08-02
---
# Cart & Checkout — Overview

## What is this? (for everyone)
This is the shopping basket every customer (including guests browsing before they've logged in)
builds up while ordering, and the process that turns it into a placed order. A cart can hold items
from more than one restaurant at once, keeps its totals live as things change, and survives a
customer logging in partway through — including keeping whatever discount they'd already locked in.

Before an order is actually created, checkout runs a long list of checks: is delivery timing
realistic, is the address valid and not in an overloaded area, do the restaurants deliver there, are
prices still current, and — if a promo code or voucher was used — is it actually valid for this
order. Only one of a promo code or a voucher can be used per order, never both.

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Restaurant menu | Customer / Guest | Add items to cart, optionally across multiple restaurants |
| 2 | Cart summary | Customer / Guest | Review items, quantities, running total, price-change warnings |
| 3 | Login (mid-cart) | Guest | Cart, address, and locked discount carry over to the real account |
| 4 | Checkout | Customer | Choose delivery time/address/payment split, place the order |

## Business Flow (plain language)
1. Items get added to the cart from one or more restaurants. Adding the exact same item again just
   increases its quantity.
2. If a restaurant changes a price while an item sits in someone's cart, that line is flagged so the
   customer sees the new price before paying.
3. A guest can build a full cart, including locking in a discount, before ever logging in. The moment
   they do log in (to an existing account), their guest cart entirely replaces whatever that account
   already had — nothing is combined, the guest's items and discount simply win.
4. At checkout, delivery timing, address, area load, restaurant coverage, and pricing are all
   re-checked. A promo code or a voucher can discount the order — never both together.
5. Once everything passes, the cart becomes an `Order` (see the Order & Fulfilment feature).

## Key Concepts
- **Multi-store cart** — one cart, multiple restaurants, up to a configured limit.
- **Price-changed line** — a cart item flagged because its price moved since it was added; must be
  acknowledged before checkout.
- **Guest-replaces merge** — logging in as a guest doesn't combine carts, it swaps in the guest's.
- **Locked Tiered Discount** — see [[Customer Ordering/Tiered Discount/_overview|Tiered Discount]] for what gets
  carried across the login transition.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — for developers & CR work.
- [[_scenarios|Scenario Catalog]] — what happens in each case.
