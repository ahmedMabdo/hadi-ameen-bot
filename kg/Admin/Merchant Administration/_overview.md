---
id: 8orders/admin/merchant-administration/overview
title: Merchant Administration — Overview
note_type: overview
context: Admin
feature: Merchant Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, merchant-administration, business]
---
# Merchant Administration — Overview

## What is this? (for everyone)

8Orders' side of the relationship with restaurants: signing them up, holding their details, dealing with
complaints about them, scoring how well they perform, and settling their account.

It starts with an enquiry — a restaurant asks to join. That becomes a lead in 8Orders' sales system,
and if it goes ahead, a restaurant record. From then on this feature is where 8Orders staff maintain
that record, force a store closed if something is wrong, record customer complaints, and see the store's
performance score.

One thing worth knowing up front: **a restaurant's full profile can only be edited here.** The
restaurant's own portal deliberately cannot do it — merchants manage their menu, orders and staff, but
not their own commercial details.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Sign-up enquiries | Commercial | Restaurants asking to join |
| 2 | Restaurant profile | Commercial, operations | The full record — 47 different screens' worth |
| 3 | Force busy / available | Operations | Stop or resume a store taking orders |
| 4 | Complaints | Support | Customer complaints about a store or order |
| 5 | Rejected-order reasons | Operations | The reason catalogue behind rejection statistics |
| 6 | Performance score | Commercial | Which band a store falls into |
| 7 | Merchant account | Finance | Transactions and settlement |
| 8 | Merchant reports | Commercial | Reporting on stores |

## Business Flow (plain language)

1. A restaurant enquires. The enquiry becomes a lead in the sales system, and its progress is tracked
   back into 8Orders.
2. If it proceeds, a restaurant record is created and its commercial details maintained here.
3. In operation, staff can force a store closed, and customers' complaints are recorded against the
   store and the order.
4. A complaint may be linked to a compensation paid to the customer. If that compensation is later
   removed, the link is cleared rather than left dangling.
5. Rejection rates and extra deliveries are weighted into a score that places each store in a band —
   Good, Monitor, High Risk or Critical.
6. Finance settles the merchant's account, and those movements are sent to the accounting system.

## What a business reader must know

**The performance thresholds are the same for every restaurant.** The weights and band boundaries are
held as a single platform-wide setting, not per restaurant. So "score this chain differently from that
independent" is not something the system can currently express — it would require a change, not a
configuration.

**Complaints are recorded with no validation.** The complaint record accepts what it is given: it does
not verify that the order exists, that the reason is a real reason, or that a complaint marked as
compensated actually has a compensation attached. Whatever checking happens is done by the screen that
creates it, which means two different screens could apply different standards. Nothing has gone wrong
because of this that we can see — it is a fragility, not an incident.

**One merchant report screen has its sign-in requirement commented out**, leaving it reachable without
signing in. That is recorded.

Two smaller points that matter for planning:

- Some of this feature's validation messages are written in **Arabic inside the core system code**,
  which means an English-speaking user can see untranslatable Arabic text, and monitoring that looks for
  English error text will not see these failures.
- The main restaurant screen is very large — 47 separate operations in one place. Any change there needs
  care about which of those 47 the admin app actually uses.

Register rows: #570 (report list without sign-in), #620 (complaint record without validation), #621
(Arabic domain messages and the global scoring singleton).

## Key Concepts

- **Lead** — a restaurant sign-up enquiry, tracked in the sales system.
- **Complaint** — a customer's grievance about an order or store, optionally linked to a compensation.
- **Rejection rate** — how often a store refuses orders; a major input to its score.
- **Score band** — Good, Monitor, High Risk, Critical.
- **Force busy** — 8Orders stopping a store from taking orders, as opposed to the store doing it itself.

## Detailed Notes

- [[Admin/Merchant Administration/_knowledge-graph|Technical Knowledge Graph]] — the complaint
  aggregate, the KPI singleton, and every controller.
- [[Admin/Merchant Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[Restaurant.business|Restaurant]] · [[Restaurant Portal/Merchant Account & Access/_overview|Merchant
  Account & Access]] — what the merchant can do for themselves.
