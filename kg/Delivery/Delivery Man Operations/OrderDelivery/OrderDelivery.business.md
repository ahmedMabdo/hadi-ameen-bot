---
id: 8orders/delivery/delivery-man-operations/orderdelivery-business
note_type: business
context: Delivery
feature: Delivery Man Operations
entity: OrderDelivery
entity_type: child
last_updated: 2026-08-23
tags: [delivery, financial, business]
---
# OrderDelivery

The delivery-side record of one order's fulfillment — who's assigned, its progress, and the cash
reconciliation between what the delivery man collected and what they're owed.

## What it is
When an order needs delivering, a record tracks which delivery man is assigned (and any
support/backup delivery man), the delivery's progress (assigned → viewed → on the way → completed),
and — this is the financially important part — a running reconciliation of how much cash the delivery
man collected from the customer, how much they paid out to restaurants along the way, and how that
nets against their own profit entitlement for the trip.

## Business rules (plain words)
- If the delivery man ends up holding more cash than they're owed in profit, the extra is money they
  owe the company. If they're holding less cash than their profit (or negative, because they paid
  restaurants more than they collected), the company owes them the difference.
- A delivery can be handed off between delivery men (a "parent"/supporting relationship) — cash and
  profit accounting follows whoever actually owns the order at that point.
- There's no single explicit status field shown to a caller — the delivery's stage is inferred from
  which date fields are set (assigned/viewed/on-way/completed), in priority order.

## Who uses it
- **Roles:** Delivery Man (progresses the delivery), Admin/back-office (reconciliation, corrections).

## Related
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — posts ledger entries for the cash/profit this record computes
- Technical detail: [[OrderDelivery.technical|OrderDelivery — technical]]
