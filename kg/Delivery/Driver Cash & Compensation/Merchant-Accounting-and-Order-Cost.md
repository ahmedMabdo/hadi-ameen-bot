---
id: 8orders/delivery/driver-cash-and-compensation/merchant-accounting-and-order-cost
note_type: single
context: Delivery
feature: Driver Cash & Compensation
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs
    sha1: 950a66f2f1c5
  - path: Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs
    sha1: 3d2416f9aed1
  - path: Shared/TalabatkLogic/TalabatkModels/RoboCall.cs
    sha1: ffb4771ff313
last_updated: 2026-08-23
tags: [delivery, financial, technical, backend-domain]
---
# MerchantStatementTransaction, OrderCostHolder, RoboCall, Notification

Grouped lighter-touch coverage — no full separate notes, but real points worth recording.

## MerchantStatementTransaction
`Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs`. The restaurant-side twin of
[[DeliverymanTransaction.technical|DeliverymanTransaction]] — same shape
(private-constructor ledger row, one validated `Instance` gate, ~13 named factory wrappers, an
exhaustive `IsTransactionCredit` switch mapping every type to a fixed direction). The `Instance` gate
(`Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs:29-63`) validates: `accountId` required for `Add`/`Deduction`; `merchant` required; `amount > 0`
(stricter than `DeliverymanTransaction`'s equivalent, which has no amount guard at all); `comment`
non-null; `entityId` required for `Order`. A well-built, internally-consistent parallel to the
delivery-side ledger — no bugs found here.

## OrderCostHolder
`OrderCostHolder.cs`. Tracks who's financially responsible when an order's cost needs to be split
across driver/agent/specific restaurants (e.g. an undelivered order). Real guard worth noting:
`Instance` (`Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs:44-75`) only attributes a `DriverId` **if** `driverDeductibleAmount > 0`
(`Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs:60` — `DriverId = driverDeductibleAmount > 0 ? driverId : null`) — no driver attribution without an
actual deductible tied to them. `AddRestaurantDeductibles` (`Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs:77-98`) similarly filters out any
restaurant with a zero/negative deductible before adding it.

## RoboCall
`RoboCall.cs`. An automated phone call (to a restaurant or customer) tracking record — `Instance`
(`Shared/TalabatkLogic/TalabatkModels/RoboCall.cs:46-84`) validates call id, phone number, and requires at least one associated order; `Update`
(`Shared/TalabatkLogic/TalabatkModels/RoboCall.cs:86-98`) has none of those guards (same create/update asymmetry pattern established elsewhere).

## Notification
`Notification.cs`. A pure data class — properties only, zero behavior, not even a factory method.

## Related
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — the delivery-side equivalent ledger
- [[Compensation|Compensation]] — `OrderCostHolder`'s presence on an order changes `MerchantStatementTransaction.AddCompensationTransaction`'s comment wording

## Open Questions
- [ ] `OrderCostHolderRestaurant`, `RoboCallOrder` not opened in full.
