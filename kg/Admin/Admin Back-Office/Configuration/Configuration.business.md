---
id: 8orders/admin/admin-back-office/configuration-business
note_type: business
context: Admin
feature: Admin Back-Office
entity: Configuration
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [admin, config, business]
---
# Configuration (System Configuration)

The single, system-wide settings row — over 100 numeric/flag settings governing order distribution
timing, delivery-man assignment tolerances, loyalty points economics, review-ranking weights,
accounting account-ID mappings, and more.

## What it is
Rather than each subsystem having its own settings table, almost every tunable number in the
platform — how long before an order auto-escalates through distribution stages, how many loyalty
points a currency unit earns, which accounting ledger account a given money movement posts to, how
delivery-man reviews get weighted by recency and rank — lives on one shared configuration row.

## Business rules (plain words)
- Some settings groups (delivery-assignment timing/tolerances) are validated when changed — you
  can't set a negative time or an out-of-range percentage. Most other settings groups (accounting
  account mappings, loyalty-points economics, review-ranking weights, core order-distribution timing)
  currently accept any value at all when changed, including ones that clearly shouldn't be valid
  (e.g. a negative time or amount) — see the technical note's flagged inconsistency.
- The daily pickup-tag numbering cap (`PickupTagMaxValue`, ties to
  [[OrderRestaurantDetails|OrderRestaurantDetails]]'s
  pickup tag) must be a positive number.
- Redeeming loyalty points into cash uses a fixed conversion formula off these settings.

## Who uses it
- **Roles:** Admin (the only plausible editor of system-wide settings — via `AdminUi`, not yet
  confirmed which screens); read by essentially every other context's Application-layer logic.

## Related
- Technical detail: [[Configuration.technical|Configuration — technical]]
