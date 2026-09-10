---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/offers-business
note_type: business
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: Offers
entity_type: child
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, transactional, business]
---
# Offers (Menu-Item Promotions)

A restaurant-level promotion — a discount on specific menu items, active on certain days and hours,
distinct from platform-wide PromoCodes/Vouchers/Tiered Discount.

## What it is
A restaurant can run an "offer": a set of specific menu items discounted (by percentage or fixed
amount), active only during configured days of the week and hours of the day, within an overall date
range. Offers can optionally cap the maximum discount per order and set a minimum order total to
qualify. The discount cost can be split between the merchant and the platform via a contribution
percentage.

## Business rules (plain words)
- An offer needs at least two descriptions (presumably Arabic and English) and at least one
  discounted item to be created at all.
- If a maximum-discount cap is turned on, the cap itself must be a positive number.
- The offer is only active during its configured days of the week and time window — outside that
  window it's treated as closed, the same way a restaurant's opening hours work.
- The cost of the discount can be shared between merchant and platform by percentage.

## Who uses it
- **Roles:** Restaurant Portal (merchant sets up/manages offers — not yet confirmed which screen,
  pending that context's own pass), Customer (sees/benefits from the discount while browsing/ordering).

## Related
- [[MenuItem.technical|MenuItem]] / [[MenuItem.business|MenuItem (business)]]
- [[Restaurant.technical|Restaurant]]
- Technical detail: [[Offers.technical|Offers — technical]]
