---
id: 8orders/admin/order-and-customer-administration/overview
title: Order & Customer Administration — Overview
note_type: overview
context: Admin
feature: Order & Customer Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, order-and-customer-administration, business]
---
# Order & Customer Administration — Overview

## What is this? (for everyone)

The operations desk. When an order goes wrong, this is where an 8Orders staff member steps in: reassign
it to another driver, put it back a step, add a note, refund the customer, or correct what the restaurant
is owed. It is also where staff look a customer up when they call, and where the promotional tools —
promo codes, vouchers, accepted payment methods, wallet top-up reasons — are maintained.

The defining characteristic of this feature is that **almost everything it does is an override**. The
order already had a status; a driver was already assigned; the payment was already taken; the merchant's
settlement was already calculated. Every action here changes a decision the system already made, which
is why who may use it matters.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Order list and detail | Operations | Find and inspect an order |
| 2 | Swap driver | Operations | Move a live order to another driver |
| 3 | Un-confirm order | Operations | Put a confirmed order back a step |
| 4 | Delivery comment | Operations | Record a note against a delivery |
| 5 | Refund | Finance, senior operations | Reverse a customer's online payment |
| 6 | Fix merchant statement | Finance | Correct what a restaurant is owed |
| 7 | Customer lookup | Support | Find a customer, their history and tags |
| 8 | Promo codes and vouchers | Marketing | Create and manage discounts |
| 9 | Payment methods | Operations | Which methods customers may use |
| 10 | Wallet top-up reasons | Finance | Why a customer's wallet was adjusted |

## Business Flow (plain language)

1. A customer or restaurant reports a problem with an order.
2. Staff find the order and choose an intervention: reassign the driver, put the order back, add a note,
   or refund.
3. If money must be returned, the refund screen reverses the payment. Depending on how far the payment
   had progressed, this is either a cancellation of the authorisation or a genuine return of funds.
4. If the restaurant's settlement was wrong, staff correct those records directly.
5. Separately, marketing runs promo codes and vouchers, and finance maintains the reasons used when a
   customer's wallet is topped up.
6. Everything done here flows into the nightly accounting hand-off.

## What a business reader must know

**The refund screen has no permission check.** The order screens generally do — twenty-five of them
require a specific permission — which makes the exceptions notable rather than merely untidy. Among the
actions with no permission requirement are: **refunding a customer's payment**, **rewriting a
restaurant's settlement**, reassigning a live order, putting an order back a step, and looking up any
customer's order history and tags. All of them are available to anyone signed in to the back office. The
refund action sits between two actions that *do* carry a permission requirement, so it was skipped rather
than deliberately left open.

**A "successful" refund may not be a refund.** Depending on how far the payment had gone, the system
either cancels the authorisation (a void) or returns captured funds (a refund). The screen's response
tells the difference, but the two have different consequences for what the customer's bank shows and for
how the money appears in the accounts. Anyone reconciling refunds needs to know which happened.

**Audit is thin for these actions.** The refund records the name of the staff member who did it, and
that is the extent of it. There is no separate approval step and no recorded reason.

Register row: #622.

## Key Concepts

- **Override** — an action that changes a decision the system already made. Most of this feature.
- **Void vs refund** — cancelling an authorisation versus returning captured funds; the system chooses
  based on payment state.
- **Merchant statement fix** — correcting the record of what a restaurant is owed.
- **Wallet top-up reason** — the category recorded when a customer's balance is adjusted.
- **Customer tag** — a label used to segment or flag a customer.

## Detailed Notes

- [[Admin/Order & Customer Administration/_knowledge-graph|Technical Knowledge Graph]] — every ungated
  action, and the refund path in full.
- [[Admin/Order & Customer Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[Order.business|Order]] · [[Customer.business|Customer]] · [[Money-Path.business|The Money Path]]
