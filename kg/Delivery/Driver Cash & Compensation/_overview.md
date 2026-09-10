---
id: 8orders/delivery/driver-cash-and-compensation/overview
title: Driver Cash & Compensation — Overview
note_type: overview
context: Delivery
feature: Driver Cash & Compensation
audience: Business
last_updated: 2026-08-23
tags: [delivery, driver-cash-and-compensation, business]
---
# Driver Cash & Compensation — Overview

## What is this? (for everyone)

Money between 8Orders and its delivery drivers, in both directions.

A driver who delivers a cash order is holding 8Orders' money from the moment the customer pays. A
driver who earns a bonus, or is compensated for a delivery that went wrong through no fault of theirs,
is owed money by 8Orders. This feature keeps the running total and decides what happens when it gets
too large.

The mechanism is a **ledger**: every event adds a line — cash collected, delivery fee earned, bonus
credited, compensation paid, deposit made. Nothing is ever edited or deleted; a mistake is corrected by
adding another line. The driver's balance is the sum of those lines, not a number someone types.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Deliver a cash order | Driver | Driver now holds 8Orders' money |
| 2 | Balance / statement | Driver | See what they owe or are owed |
| 3 | Blocked from new orders | Driver | What happens when they hold too much cash |
| 4 | Deposit at a Fawry point of sale | Driver | Hand the cash back and clear the balance |
| 5 | Bonus | Driver | Extra earnings from a bonus scheme |
| 6 | Compensation | Driver, 8Orders staff | Payment for a delivery that went wrong |
| 7 | Cashier receipt | 8Orders back office | Record cash taken or paid at the office |

## Business Flow (plain language)

1. A driver delivers a cash order. Two lines are added: what they collected (they owe it) and what they
   earned (8Orders owes them).
2. The balance rises as they deliver more cash orders without depositing.
3. When it passes the limit set for their city, **the driver stops being offered new orders.** This is
   the feature's real teeth — it is a cash-risk control, not an accounting nicety.
4. The driver goes to a Fawry point of sale and deposits. Fawry tells 8Orders, the deposit is credited,
   the balance falls, and they return to normal work.
5. Separately, bonuses and compensation add to what 8Orders owes them.
6. The back office can also record cash taken or paid at the office directly.
7. Every one of those movements is also sent to 8Orders' accounting system daily.

## What a business reader must know

**Four different things can change a driver's balance, and they do not know about each other.** A
delivery, a Fawry deposit, a cashier at the office, and a nightly batch all write to the same running
total, through four unrelated paths. Nothing reconciles them against one another. If two of them
disagree about the same money, the ledger simply contains both. Any change to how the balance is
calculated has to be checked against all four, and three of them live outside this part of the system.

**The Fawry deposit path is the best-secured integration in 8Orders**, and that is worth knowing for a
positive reason. Fawry's servers call 8Orders without a login — as they must — but every one of those
calls carries a cryptographic signature that 8Orders checks against a shared secret before acting, and
rejects if it does not match. Several problems recorded elsewhere in this knowledge graph are precisely
the *absence* of this pattern on other unauthenticated endpoints. So when someone asks "can we secure
that webhook?", the answer is yes, and there is a working example in this same app.

**Money is never edited.** Because the ledger is append-only, a correction is a new line, not a change
to an old one. That is the right design, and it means "fixing" a balance in the database directly would
break the audit trail rather than repair it.

## Key Concepts

- **Ledger line** — one typed credit or debit against a driver. The unit everything here is made of.
- **Balance / required payment** — the sum of the lines: what the driver currently owes 8Orders.
- **Cash limit** — the per-city ceiling. Above it, the driver is taken out of order rotation.
- **Fawry deposit** — handing collected cash back at a Fawry point of sale.
- **Bonus** — extra earnings from a scheme, credited to the driver.
- **Compensation** — a payment for a delivery that went wrong.

## Detailed Notes

- [[Delivery/Driver Cash & Compensation/_knowledge-graph|Technical Knowledge Graph]] — the four
  triggers, the Fawry endpoints and their verification, the ledger-to-balance derivation.
- [[Delivery/Driver Cash & Compensation/_scenarios|Scenario Catalog]] — what happens if…
- [[Driver-Cash-Cycle.business|The Driver Cash Cycle]] — the end-to-end money movement in plain words.
- [[DeliverymanTransaction.business|Deliveryman Transaction]] — the ledger line itself.
- [[Compensation|Compensation]] · [[DeliveryBouns.business|Delivery Bonus]]
