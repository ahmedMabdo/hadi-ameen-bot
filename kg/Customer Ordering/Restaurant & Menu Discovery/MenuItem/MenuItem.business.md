---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/menuitem-business
note_type: business
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: MenuItem
entity_type: child
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, master, business]
---
# Menu Item

Something a customer can order — a dish, a grocery product, a drink.

## What it is
Every item a customer sees on a restaurant or Mart's menu. Items can go temporarily unavailable
(sold out for the day) or be fully deactivated, and Mart items track live stock counts.

## Business rules (plain words)
- When a restaurant marks an item unavailable, how long it disappears depends on the reason given —
  anywhere from an hour to effectively a full year.
- If a restaurant keeps rejecting the same item from orders in one shift, it gets hidden for
  progressively longer each time — this discourages accepting orders for things that aren't
  actually available.
- Mart items go out of stock automatically when their count hits zero, and come back automatically
  once restocked.

## Who uses it
- **Roles:** Customers browse and order; restaurant/mart staff manage availability and stock.
- **Screens:** Restaurant/Mart menu, item detail, search results.

## Related
- [[Restaurant.business|Restaurant]]
- Technical detail: [[MenuItem.technical|MenuItem — technical]]
