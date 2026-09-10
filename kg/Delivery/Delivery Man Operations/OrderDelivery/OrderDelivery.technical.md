---
id: 8orders/delivery/delivery-man-operations/orderdelivery-technical
note_type: technical
rule_count: 4
context: Delivery
feature: Delivery Man Operations
entity: OrderDelivery
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs
    sha1: f86d116d0efc
last_updated: 2026-08-23
tags: [delivery, financial, technical, backend-domain]
---
# OrderDelivery — Technical

> **Layer:** Backend-Domain — legacy entity, event-raising, no private constructor.
> **Context:** Delivery.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Cash-vs-profit reconciliation — the core financial calculation
- **Plain language:** Compares how much cash the delivery man is net holding (what they collected,
  minus what they paid out to restaurants) against their profit entitlement for the delivery, and
  determines which direction money needs to move.
- **Source:** `CalculateDeliveryNets(cashAfterCompensation, orderCash)` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:282-325`):
  - `totalCollectedFromCustomer = (isOrderOwner && cashAfterCompensation >= 0) ? cashAfterCompensation : 0`
  - `cashAmount = isOrderOwner ? orderCash : 0`
  - `totalCashAmountDeliveryHas = cashAmount - TotalPaidToRestaurants`
  - if `== 0` → `DeliveryManNet = DeliveryManProfit` (holding net-zero cash, so the company owes them their full profit)
  - if `> 0` and `>= DeliveryManProfit` → `EightOrdersNet = cash - profit` (holding more than their profit; the excess is owed **to** the company)
  - if `> 0` and `< DeliveryManProfit` → `DeliveryManNet = profit - cash` (holding some cash but less than their profit; company owes the shortfall)
  - if `< 0` → `DeliveryManNet = abs(cash) + profit` (paid out more to restaurants than collected; company owes that shortfall plus their full profit)
  - `isOrderOwner = !DeliveryManParentId.HasValue` — a supporting/handed-off delivery man (has a parent) contributes neither collected cash nor order cash to this calculation.

### Rule 2: ⚠️ Possible bug — the two net fields are never reset to 0 in the branches that don't set them
- **Plain language:** Each branch of the reconciliation above sets only one of two "who owes whom"
  fields — but never clears the other one. If this method runs more than once for the same delivery
  (e.g. after a correction) and the outcome moves from one branch to another, the previous branch's
  value can linger.
- **Source:** `CalculateDeliveryNets` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:282-325`) — the `== 0` and `< 0` branches only assign
  `DeliveryManNet`; the `> 0 && >=` branch only assigns `EightOrdersNet`. Neither branch zeroes the
  other field. If a first call lands on the `EightOrdersNet` branch and a later recalculation (say,
  after a compensation changes `cashAfterCompensation`) lands on a `DeliveryManNet` branch instead,
  `EightOrdersNet` keeps its stale prior value alongside the newly-set `DeliveryManNet` — both fields
  would then read as "owed" simultaneously. Not confirmed whether `CalculateDeliveryNets` is ever
  actually called more than once for the same row in practice.

### Rule 3: Status is inferred from which date fields are populated, in priority order
- **Source:** `GetOrderDeliveryStatus(isPushZone)` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:127-161`) — checks, in order: `Completed`
  status id → `"Completed"`; `OnWayDate` set → `"OnWay"`; `ViewDate` set → `"View"`; `AssignDate` set
  → `"Assign"`; `Timeout` status id → `"Time Out"`; else if `isPushZone` → `"Processing in Auto Assign
  Queue"`; else `"New"`. Same "no explicit state machine, inferred from field combination" shape
  already established as the norm across this codebase.

### Rule 4: A manually-managed version stamp, not EF's built-in concurrency token
- **Source:** `Version` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:63`, initialized to a Unix-millisecond timestamp) is explicitly
  reassigned inside `AssignDeliveryManToRequest` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:225`) and `CompleteOrderDelivery` (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:268`) — a
  hand-rolled optimistic-concurrency-style marker, not EF Core's `[Timestamp]`/`RowVersion`
  mechanism. Not confirmed how (or whether) this is actually checked anywhere to prevent
  lost-update races.

## Key Fields
| Field | Meaning |
|-------|---------|
| `DeliveryManParentId` | Set when this delivery is a hand-off/support role — see `SwapToAnotherParentDelivery`/`ChangeDeliveryManParent` |
| `TotalCollectedFromCustomer` / `TotalPaidToRestaurants` / `DeliveryManProfit` | Inputs to Rule 1 |
| `EightOrdersNet` / `DeliveryManNet` | Outputs of Rule 1 — see Rule 2's flagged reset gap |
| `ShiftBouns` / `DeliveryBounsId` | Ties to [[DeliveryBouns.technical\|DeliveryBouns]] |

## Related
- Business view: [[OrderDelivery.business|OrderDelivery]]
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — `AddCashOrderTransaction` reads `TotalCollectedFromCustomer`/`DeliveryManProfit` directly from this entity
- [[DeliveryBouns.technical|DeliveryBouns]]

## Open Questions
- [ ] Whether `CalculateDeliveryNets` (Rule 2) is ever invoked more than once for the same row, which
  would be needed to actually trigger the stale-field issue.
- [ ] How/whether `Version` (Rule 4) is checked to prevent concurrent-update races — not traced to a
  caller.
- [ ] `OrderRestaurantDelivery`, `AutoAssignRequest`, `DeliveryMenMoneyRequest` referenced but not
  opened in full.
