---
id: 8orders/customer-ordering/order-and-fulfilment/ordercomplaint
note_type: single
context: Customer Ordering
feature: Order & Fulfilment
entity: OrderComplaint
entity_type: aggregate-root
rule_count: 7
sources:
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs
    sha1: e2151a2ca10b
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, transactional, technical, backend-domain]
---
# OrderComplaint

> Confirms an earlier, unverified finding directly: this aggregate's `Create` genuinely has zero
> validation, in contrast to the other, more mature aggregates in `Shared/TalabatkLogic`
> (`TieredDiscount`, `DeliveryAnnouncement`, `DeliveryManNotification`).

A customer complaint against an order, optionally tied to a compensation payout or an outgoing
(external) delivery replacement order. `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs`.

## Business rules
- **`Create` has no validation at all** (`:29-58`) — no check that `orderId`/`orderComplaintReasonId`
  are valid, no check on `complaintOn`. The only defensive touches are cosmetic:
  `ComplaintOn`/`CreatedBy` default to empty string if null; `OutGoingDeliveryOrderId` is nulled out
  if `<= 0`; `OutGoingDeliveryOrderCode` is nulled out if blank (trimmed otherwise). None of this is
  business validation — this is the least-guarded aggregate-style entity found in this pass.
- **`DetachCompensationLink()`** (`:61-64`) clears the FK to a `Compensation` row — the doc comment
  states this is used "when the linked compensation row is removed (e.g. delete while `InReview`)" —
  implying `Compensation` can be deleted while still in review, and this method exists specifically
  to keep `OrderComplaint` from pointing at a now-deleted row.

## Rule / Decision Matrix

A complaint raised against an order, and the link to the compensation it may produce. One of the four DDD aggregates in the codebase — and the one that behaves least like one.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | `Create` returns a plain `OrderComplaint`, not a `Result` | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | So an "aggregate root" with no representable failure — 🔴 `_conflicts.md` #620 |
| 2 | No guard on any field | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | Reason, payment method, order and creator are all assigned as given |
| 3 | The complaint records which side it is against | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | `ComplaintOn` — restaurant or driver — which is what routes it to the right KPI |
| 4 | Compensation is linked, not owned | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | `IsCompensation` plus `CompensationId`, so a complaint can exist with or without money attached |
| 5 | The compensation link can be severed | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:61` | `DetachCompensationLink` — the only lifecycle method, and it is a `void` |
| 6 | Outgoing-delivery complaints carry their own order reference | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | `IsOutGoingDelivery`, `OutGoingDeliveryOrderId` and `OutGoingDeliveryOrderCode` — because that order did not originate in the app |
| 7 | Action is attributed separately from creation | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29` | `CreatedBy`/`CreationDate` and `ActionBy`/`ActionDate`, so raising and resolving are distinguishable |

> The reason vocabulary and its weights are `OrderComplaintReason` (Arabic-only validation message,
> 🔴 #621) and `OrderComplaintReasonType` — see
> [[Customer Ordering/Order & Fulfilment/Order-Lifecycle.technical|Order Lifecycle]].

## Related
- [[Order.technical|Order]]
- [[Compensation|Compensation]] — optional link, cleared via `DetachCompensationLink`
- [[Order.ExternalDelivery|Order — External Delivery Extension]] — `IsOutGoingDelivery`/`OutGoingDeliveryOrderId` tie a complaint to a replacement external-delivery order

## Open Questions
- [ ] What (if anything) validates a complaint before this factory is called — not traced to the
  Application-layer command handler.
- [ ] `OrderComplaintReason`, `OrderComplaintReasonType`, `MerchantKpiScoreConfiguration` (same
  aggregate folder) not opened in this pass.
