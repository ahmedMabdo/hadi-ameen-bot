---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/restaurantreview
note_type: single
rule_count: 7
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: RestaurantReview
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/AddRestaurantAndDeliveryReviewsCommand/AddRestaurantAndDeliveryReviewsCommand.cs
    sha1: ec6f331336ee
  - path: Shared/TalabatkApplication/Commands/AddRestaurantReviewCommand/AddRestaurantReviewCommand.cs
    sha1: f39a985c61c9
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRejectedReason.cs
    sha1: ece55022d788
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs
    sha1: 84af799ed021
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, transactional, technical, backend-domain]
---
# RestaurantReview (+ OrderRejectedReason)

## RestaurantReview
`Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs`. A customer's rating/comment on a
restaurant after an order.

- **Content-moderation state machine:** a new review update marks `IsNew=true`, `Active=false`
  (pending moderation) via `UpdateReview`/`UpdateReviewV2` (`:74-98`); `SetReviewAsPublished` (`:109-117`)
  flips `Active=true`, `IsNew=false`, stamps a publish date; `SetReviewAsUnPublished` (`:119-125`)
  reverses just the active flag.
- **⚠️ Likely dead code:** `CalcRate(orderpackaging, foodquality, valueprice)` (`:68-71`) — a private
  static average-of-three-scores formula — is defined but **never called** anywhere in this file.
  Both `UpdateReview` and `UpdateReviewV2` set `Rate` directly from an already-computed value passed
  in, rather than deriving it via `CalcRate` from the three sub-scores also being set at the same
  time. Either the sub-score-to-overall-rate computation happens upstream (Application layer, not
  traced) and this method is vestigial, or it's a real gap where the three sub-scores and the overall
  `Rate` could drift out of sync.
- `UpdateReview(RestaurantReview restuarantreview)` takes a whole other `RestaurantReview` instance as
  its parameter rather than individual fields — an unusual signature worth noting, not necessarily a
  bug.
- **Application layer** (`AddRestaurantReviewCommand.cs`): upserts by `CustomerId`+`RestaurantId`+
  `OrderId` (update if an existing review for that triple is found, insert otherwise), and gates on
  the order/restaurant/customer combination actually existing via `OrderDetails` before allowing a
  review at all. If any of the 4 sub-ratings (`Rate`/`OrderPackaging`/`ValueForPrice`/`FoodQuality`)
  falls below the configured `BadReviewNumber` threshold, it fires `IApiClientHandler.NewBadReview()`
  — a notification hook for low review alerts. Minor gap: the "combination not found" path returns
  `CQRSResponse { Success = false }` with no `ErrorMessage` set, unlike every other failure branch in
  the same handler.
- **`AddRestaurantAndDeliveryReviewsCommand.cs`** — a second, batched entry point: submits reviews for
  one or more restaurants **and** a delivery man review in a single call (used when an order has
  multiple restaurants). Same upsert-by-key logic as above, plus a `DeliveryManReview` upsert keyed on
  `DeliveryManId`+`OrderId`. **⚠️ Confirmed bug:** on save failure it returns
  `CQRSResponse { Success = true, ErrorMessage = "Server Error" }` (`:118-123`) — `Success` is `true`
  inside the `if (!saveResult.IsSuccess)` branch, so a failed save is reported to the caller as a
  success. Separately, `AddRestaurantReivewCommentEvent()` (`:126-127`) is only raised for newly
  inserted reviews, never for updated ones — not confirmed whether that asymmetry is intentional.

## OrderRejectedReason
`OrderRejectedReason.cs`. A configurable reason a restaurant can reject an order for — light
reference entity, no embedded validation in `Instance`/`Update`. `AutoBusyMinutes` ties to
`IsAutoBusyForResturantsEnabled` (`Configuration`) — presumably how long a restaurant is auto-marked
busy after using this rejection reason; not traced to that logic in this pass.

## Rule / Decision Matrix

A customer's rating of a restaurant, on four axes, tied to the order it came from. Seven methods and **no guards at all** — including on the rating values themselves.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | A review is tied to an order | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:32` | `Instance` takes `OrderId`, so reviews are anchored to a real purchase |
| 2 | Four independent scores, none range-checked | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:32` | `Rate`, `OrderPackaging`, `ValueForPrice`, `FoodQuality` — nothing rejects 0, 11 or a negative |
| 3 | A comment raises a domain event | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:57` | `AddRestaurantReivewCommentEvent` — this is what reaches the outbound webhook subscribers |
| 4 | Two update paths with different field coverage | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:74` | `UpdateReview` and `UpdateReviewV2` (`:89`) both return `Result` and neither can fail |
| 5 | Publication is a separate lifecycle from creation | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:109-119` | `SetReviewAsPublished`/`SetReviewAsUnPublished` with a `PuplishDate` (misspelt) — so a review can exist unpublished |
| 6 | `IsNew` is a moderation queue flag | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:103` | `SetAsNew` returns `Result` and cannot fail |
| 7 | Edits are attributed | `Shared/TalabatkLogic/TalabatkModels/RestaurantReview.cs:74` | `LastModifiedAt` and `ModifiedByUserName` record who changed a customer's words |

> Reading a single review by id has no restaurant-ownership filter — 🟡 `_idor-instances.md` instance 29,
> recorded as `likely` because id guessability was not verified.

## Related
- [[Restaurant.technical|Restaurant]]

## Open Questions
- [ ] Whether `CalcRate` is genuinely dead code or called from somewhere not traced in this pass.
- [ ] How `AutoBusyMinutes` actually drives restaurant busy-state — not traced.
