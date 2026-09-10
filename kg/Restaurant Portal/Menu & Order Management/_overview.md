---
id: 8orders/restaurant-portal/menu-and-order-management/overview
title: Menu & Order Management — Overview
note_type: overview
context: Restaurant Portal
feature: Menu & Order Management
audience: Business
last_updated: 2026-08-23
tags: [restaurant-portal, menu-and-order-management, business]
---
# Menu & Order Management — Overview

## What is this? (for everyone)

This is the restaurant's own screen in 8Orders — the one a shift supervisor keeps open all day. It does
two jobs that are really one: **decide what the restaurant sells**, and **work the orders that arrive
because of it**.

The menu side is a small catalogue: categories (Pizza, Drinks), items inside them, one or more prices
per item (small/medium/large), and options a customer can add (extra cheese, no onions). Items can be
switched on and off through the day, moved between categories, copied, or edited in bulk from a
spreadsheet. Whatever the restaurant does here is what the customer sees in the app minutes later.

The order side is a live queue. A new order appears on the screen the moment a customer places it —
pushed in real time, not polled. Staff confirm it, start cooking, and mark it ready for the driver.
If something is out of stock they can tell the customer and offer a replacement, reject part of the
order, or reject it entirely with a reason. The screen also tracks how long each stage takes, which is
what the performance reports later grade the store on.

A third, smaller job lives here too: a restaurant can ask 8Orders to deliver an order the restaurant
took itself, by phone or at the counter. Those are "external delivery requests", with their own list of
the restaurant's own customers.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Menu tree | Merchant admin, data entry | Categories, items, prices and options |
| 2 | Availability | Any store staff | Switch an item or a whole category on/off |
| 3 | Bulk edit (Excel) | Merchant admin, data entry | Change many prices or items at once |
| 4 | New orders | Store staff | The live incoming queue |
| 5 | Confirm & cook | Store staff | Accept the order and start preparing it |
| 6 | Item replacement | Store staff | Tell the customer an item is unavailable and offer alternatives |
| 7 | Reject | Store staff | Refuse some items, or the whole order, with a reason |
| 8 | Ready for pickup | Store staff | Hand the order to the driver |
| 9 | Order history | Merchant admin | Everything the store has handled |
| 10 | External delivery | Merchant admin | Ask 8Orders to deliver an order the store took itself |
| 11 | Mart catalogue | Merchant admin | Grocery-style stock, kept in step with the ERP system |

## Business Flow (plain language)

1. The restaurant builds its menu: categories, then items, then prices, then options.
2. A customer orders. The order arrives on the restaurant's screen instantly, and the store's portion
   of it starts as **New**.
3. Staff open it (**viewed**), then **confirm** it and **start cooking**.
4. If an item cannot be made, staff either notify the customer to pick a replacement, reject those
   items, or reject the whole order with a reason. Each of those is recorded against the store.
5. When the food is ready the order becomes **ready to pick up**, and the driver collects it —
   after which the order leaves the restaurant's hands.
6. Cancellations from the customer or 8Orders can interrupt at any point; the store sees the status
   change rather than acting on it.
7. Every stage transition is timestamped, which is what feeds the performance and rejection reports.

## Key Concepts

- **Category / item / price / option** — the four levels of the menu. A price row, not the item, is
  what a customer actually buys.
- **Availability** — a temporary on/off switch per item; different from deleting it and different from
  the store being closed.
- **The store's portion** — when one customer order covers two restaurants, each restaurant sees and
  works only its own portion, with its own status.
- **Item replacement** — the "we're out of X, will you take Y?" conversation, tracked as a status
  rather than a chat.
- **Ready to pick up** — the hand-over point between the restaurant and the driver; after it, delays
  are attributed to delivery, not the kitchen.
- **External delivery request** — a delivery job for an order the restaurant took itself.
- **Mart** — grocery-style stock whose quantities are synchronised with 8Orders' ERP system rather than
  typed in by hand.

## What a business reader should know about trust here

Two things, both recorded as findings rather than opinions.

**First: a second version of most order actions trusts the screen instead of the login.** When the
order screens were rebuilt, eight actions (start cooking, confirm, order details, ready-for-pickup, the
two reject paths, and two list views) were changed to take the *restaurant number from the request*
rather than from the signed-in user. In practice, a signed-in merchant who edits that number can act on
another restaurant's orders — confirm them, reject them, or read their details. The older versions of
the same actions do it correctly, and more than ten neighbouring actions in the same file still do,
which is what makes this an oversight rather than a design.

**Second: the real-time notification relay has no login at all.** The channel that pushes "new order",
"order rejected" and "delay" alerts onto restaurant screens accepts requests from anyone who knows the
address. Someone could push a fake new-order alert to a restaurant's dashboard. The same file also
allows pulling an order's report image by guessing its number.

Alongside those, five menu-management actions can **delete or alter another restaurant's menu** (an
option group, a price row, an item's availability) because they accept an identifier without checking
who owns it.

None of this is fixed by the knowledge graph — the point is that it is now written down, cited to the
line, and counted. The technical note lists every endpoint with a verdict, and the register rows are
#33, #41, #42, #43, #44, #446, #458, #585–#602, plus IDOR #4, #10, #13, #14, #15, #16, #31.

## Detailed Notes

- [[Restaurant Portal/Menu & Order Management/_knowledge-graph|Technical Knowledge Graph]] — the ERD,
  both status enums, the V1/V2 table and every endpoint verdict.
- [[Restaurant Portal/Menu & Order Management/_scenarios|Scenario Catalog]] — what happens if…
- [[Merchant-Menu-and-Orders.business|Merchant Menu & Orders]] — the entities in plain language.
- [[Customer Ordering/Restaurant & Menu Discovery/_overview|Restaurant & Menu Discovery]] — the same
  menu as the customer sees it.
