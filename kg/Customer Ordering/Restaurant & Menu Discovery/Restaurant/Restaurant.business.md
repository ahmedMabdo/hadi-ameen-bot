---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/restaurant-business
note_type: business
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: Restaurant
entity_type: child
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, master, business]
---
# Restaurant (and Mart)

A restaurant or grocery/quick-commerce store a customer can order from.

## What it is
"Restaurant" and "Mart" aren't two different things in the system — a Mart is just a restaurant
flagged as a store. Both are browsed, searched, and ordered from through the same underlying data.

## Business rules (plain words)
- Whether a restaurant shows as "open" depends on its working hours for today, including overnight
  hours (open until 2am, for example).
- A newly-onboarded restaurant can carry a "new" badge for a limited time.
- A restaurant must have at least one working day configured — it can't have zero open days.

## Who uses it
- **Roles:** Customers browse and order; restaurant staff manage their own profile via Restaurant Portal (not covered here).
- **Screens:** Home page, search, restaurant menu page.

## Related
- [[MenuItem.business|Menu Item]]
- Technical detail: [[Restaurant.technical|Restaurant — technical]]
