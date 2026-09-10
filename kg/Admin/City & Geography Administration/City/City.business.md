---
id: 8orders/admin/city-and-geography-administration/city-business
note_type: business
context: Admin
feature: City & Geography Administration
entity: City
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [admin, master, business]
---
# City

The per-city configuration hub — every city where the service operates has its own tax rates,
delivery-fee rules, delivery-man scoring weights, and financial-deduction defaults.

## What it is
Almost every operational rule that varies by geography lives on a city's own configuration row: how
many restaurants can go in one order, how far apart they're allowed to be, tax rates, delivery-man
insurance/equipment-deduction defaults, and the weighting formula used to score/rank delivery men in
that city (customer rating, working hours, delivered-order count, acceptance rate, arrival times).

## Business rules (plain words)
- A city's delivery-man scoring weights (rating, working hours, delivered orders, acceptance rate,
  restaurant/customer arrival time) must add up to exactly 1 (100%) — the system rejects saving a
  city configuration otherwise.
- Each city sets its own delivery-man financial defaults: insurance limit, minimum deposit/equipment
  deduction amounts and percentages — these feed directly into how much a delivery man in that city
  must pay when their cash balance exceeds their limit (see
  [[DeliveryMen.technical|DeliveryMen]] Rule 3, 5).
- A city can define its own delivery-man price tiers (distance/rate bands) — a fixed rate table
  distinct from any per-delivery-man override.

## Who uses it
- **Roles:** Admin (city configuration is clearly back-office — provisioning tax/fee/scoring rules).
- **Screens:** `AdminUi` city-management screen — not yet confirmed which one (pending Admin
  context's own controller pass).

## Related
- [[DeliveryMen.technical|DeliveryMen]] — reads city-level financial defaults
- [[Area-and-Country|Area]] — a city's sub-divisions
- Technical detail: [[City.technical|City — technical]]
