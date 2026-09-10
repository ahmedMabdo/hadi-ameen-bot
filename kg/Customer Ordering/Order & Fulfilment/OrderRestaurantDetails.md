---
id: 8orders/customer-ordering/order-and-fulfilment/orderrestaurantdetails
note_type: single
rule_count: 13
context: Customer Ordering
feature: Order & Fulfilment
entity: OrderRestaurantDetails
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs
    sha1: 8ca4ea189b1e
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, child, technical, backend-domain]
---
# OrderRestaurantDetails ("Portion")

One restaurant's slice of an order — the exact entity `TalabatkAPIs/CONTEXT.md` calls a **Portion**
and documents the **Daily Pickup Tag** on (`OrderRestaurantDetails.PickupTag`,
`1..PickupTagMaxValue` then wraps, keyed by delivery city per
[ADR 0003](../../../../../TalabatkAPIs/docs/adr/0003-pickup-tag-keyed-by-delivery-city.md)). This
note adds the technical fields around that already-documented business concept.
`Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs`.

## What's here beyond the Pickup Tag
- **Per-restaurant discount attribution.** Separate contribution-percentage/value pairs for
  Voucher, Offer, and Tiered Discount (`VoucherContributionPercentage/Value`,
  `OfferContributionPercentage/Value`, `TieredDiscountContributionPercentage/Value`) — each
  discount mechanism's cost is split between the platform and the merchant independently, then
  combined into `TotalDiscountsContributionValue` and, via the computed `CompanyContributionValue`
  property (`OrderRestaurantDetails.cs:63-86`), how much of each discount 8Order itself absorbs
  (as opposed to the merchant).
- **Per-restaurant status** (`RestaurantOrderStatus`, an int) — distinct from the parent `Order`'s
  own `StatusId`. Owned by the Restaurant Portal side; not enumerated in this pass.
- **Cooking/pickup tracking** — `StartCooking`/`StartCookingDate`, `IsDeliveryManArrived`/`ArrivalTime`,
  `DeliveryManPickupImage`/`PickupImageDate` — all Restaurant Portal/Delivery-side concerns.
- **A deprecated field kept for compatibility**: `TotalDiscount` has had its setter removed and is
  now purely computed, but the property itself is "kept for backward compatibility but should be
  removed after release and data migration" (verbatim comment, `OrderRestaurantDetails.cs:35`) —
  a known, self-flagged piece of debt in the code itself.

## Key Fields (Customer Ordering-relevant subset)
| Field | Meaning |
|-------|---------|
| `PickupTag` | The Daily Pickup Tag — see `CONTEXT.md` for full semantics |
| `PricewithOptionAndQuantity` | This restaurant's item subtotal within the order |
| `TotalBeforeDiscount` | Computed: `PricewithOptionAndQuantity + TotalOfferDiscountValue` |
| `CompanyContributionValue` | Computed: how much of the combined discount cost 8Order (not the merchant) absorbs, across all three discount mechanisms |
| `IsPaid` / `CashOnReceived` / `TotalAmountReceivedFromDelivery` | Per-restaurant payment/cash-collection tracking |

## Rule / Decision Matrix

One restaurant's share of an order — the "order portion" a merchant actually sees, accepts and cooks. Thirty-eight methods, 41 properties, and exactly **two** guards, both on the pickup image.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | The restaurant-facing status is its own machine, separate from the order status | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:232-279` | Eight `ChangeRestaurantOrderStatusTo*` methods — Pending, Confirmed, Rejected, ItemUnderReplacment, Canceled, ItemAvailability, ReadyToPickUp, PickedUp. All `void`, so any transition can follow any other |
| 2 | A pickup image is required to be non-empty | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:304` | "Image URL cannot be empty" — one of only two guards in 414 lines |
| 3 | Removing a pickup image that is not there fails | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:315` | "No pickup image to remove" — the other guard |
| 4 | Every discount type contributes separately and is stored twice | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:158-201` | Voucher, offer, tiered and online-payment contributions each have a percentage **and** a value, set by `SetVoucherContribution`, `SetOfferContribution`, `SetTieredDiscount` and `CalculateOnlineContributionValue` — this row is where "who paid for the discount" is finally recorded |
| 5 | Voucher contribution can be reset independently | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:182` | `ResetVoucherContribution`, mirrored by `ClearTieredDiscount` (`:404`) |
| 6 | The pickup tag is assigned to the portion, not the order | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:366` | `SetPickupTag` — per-city, per-day sequence, so a multi-restaurant order carries several |
| 7 | Cooking is tracked in three separate marks | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:337-340` | `SetRestaurantCookingTime`, `MarkOrderAsStartCooing` (misspelt), `MarkRestaurantAsArrival` |
| 8 | A penalty flag is set by its own method | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:269` | `ShouldApplyPenality` sets `ApplyPenality`; nothing here decides the amount |
| 9 | Resending to the restaurant is explicit and counted | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:221` | `ResendOrderToRestaurant`, alongside `NumberOfCalls` — the robocall chase trail |
| 10 | Auto-busy is raised from here | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:251` | `AddAutoBusyEvent` — a rejection can make the restaurant busy automatically |
| 11 | Cancellation after alternatives is a distinct outcome | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:297` | `MarkAsCanceledAfterAlternatives` sets its own flag, so "cancelled" and "cancelled after we offered substitutes" are distinguishable |
| 12 | Deletion is soft | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:361` | `SetIsDeleted` |
| 13 | The distance to the customer is stored on the portion | `Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:370` | `SetDistanceBetweenRestaurantAndCustomer` — per restaurant, because each leg differs |

## Related
- [[Order.technical|Order]] — the parent order this is one restaurant's slice of.
- Business-term background: [[../../../../Talabatk.IDS/CONTEXT|Customer Ordering CONTEXT.md]] (Daily Pickup Tag, Portion, business day sections) and its ADRs 0003/0004.
