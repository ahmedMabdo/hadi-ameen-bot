---
id: 8orders/delivery/driver-cash-and-compensation/deliverybouns-business
note_type: business
context: Delivery
feature: Driver Cash & Compensation
entity: DeliveryBouns
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [delivery, delivery-man, financial, business]
---
# DeliveryBouns (Delivery Bonus Campaign)

A time-boxed bonus campaign that pays delivery men extra based on how many orders they deliver
during a shift.

## What it is
A city runs bonus campaigns tied to a specific delivery shift and a date/time window (e.g. "deliver
during rush hour this week and earn extra per tier of orders completed"). Each campaign has tiers —
deliver enough orders and you qualify for that tier's bonus amount.

## Business rules (plain words)
- A campaign needs a name, a valid date range (start before end), and at least one bonus tier to be
  created at all.
- You cannot edit or delete a bonus campaign while it's currently active (within its date/time
  window) — only before it starts or after it ends.
- The bonus a delivery man earns is looked up by which tier their completed-order count falls into.

## Who uses it
- **Roles:** Admin (creates/manages campaigns), Delivery Man (earns the bonus, presumably shown in
  their transaction history via `DeliverymanTransaction`'s `Shift_Bouns` type).

## Related
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — `Shift_Bouns` transaction type pays this out
- Technical detail: [[DeliveryBouns.technical|DeliveryBouns — technical]]
