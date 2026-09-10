---
id: 8orders/delivery/delivery-man-operations/overview
title: Delivery Man Operations — Overview
note_type: overview
context: Delivery
feature: Delivery Man Operations
audience: Business
last_updated: 2026-08-03
---
# Delivery Man Operations — Overview

## What is this? (for everyone)
This is the delivery man's entire self-service experience in the `TalabatkDelivery` app: going
online/offline, taking breaks, seeing and accepting delivery requests, picking up and delivering
orders, splitting orders with other delivery men, tracking earnings/cash owed, and receiving
announcements and notifications.

## The Feature at a Glance
| # | Screen/Flow | Who | Purpose |
|---|---|---|---|
| 1 | Shift management | Delivery Man / Admin | Go online within an assigned shift window |
| 2 | Break | Delivery Man | Pause availability temporarily |
| 3 | Delivery requests / auto-assign | Delivery Man | See, accept, or reject incoming delivery work |
| 4 | Order lifecycle | Delivery Man | View → pick up → on-the-way → delivered/not-delivered |
| 5 | Multi-delivery-man split | Delivery Man | Request help, hand off, confirm money exchanged between delivery men |
| 6 | Earnings & balance | Delivery Man | See running balance, transaction statement, rating |
| 7 | Announcements / notifications | Delivery Man | City-wide notices and personal notifications |

## Business Flow (plain language)
1. A delivery man goes active, either within their assigned shift window or (if allowed) freely —
   see [[DeliveryMen.technical|DeliveryMen]] for the exact
   tolerance-window rule.
2. New delivery work arrives either as a direct request or through the auto-assign queue; the
   delivery man can accept or reject.
3. They pick up from the restaurant (optionally with a photo), mark on-the-way, and mark delivered —
   or not-delivered with a reason.
4. If an order needs splitting across multiple delivery men, one becomes primary and others become
   supporters; money owed between them is tracked and confirmed explicitly.
5. Cash collected, profit earned, and any bonuses/penalties all show up in the delivery man's balance
   and transaction statement.

## Key Concepts
- **Primary vs. Supporter vs. Parent delivery man** — see
  [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]] for exactly how each role's
  request-creation and assignment differ.
- **Auto-assign** — a separate accept/reject queue (`AutoAssignController`) distinct from the direct
  request flow.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — controller inventory and rule citations.
