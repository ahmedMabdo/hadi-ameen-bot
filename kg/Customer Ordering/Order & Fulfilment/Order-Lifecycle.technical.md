---
id: 8orders/customer-ordering/order-and-fulfilment/order-lifecycle-technical
note_type: technical
context: Customer Ordering
feature: Order & Fulfilment
group: Order-Lifecycle
covers: [AutoCompensationEvidenceRule, AutoCompensationQuestion, AutoCompensationQuestionOption, AutoCompensationReason, AutoCompensationRulesAuditLog, AutoCompensationSettings, DeletedOrderDetailsItemsHistory, DeliveryInterval, DeliveryInterval_Area, DeliveryIntervalsDescription, ItemReplacementReport, OrderAgentAssignment, OrderChat, OrderComment, OrderCostHolder, OrderCostHolderRestaurant, OrderCountTracking, OrderDetailReplacement, OrderDetailsOptions, OrderPayment, OrderPaymentStates, OrderRejectedReason, OrderRestaurantDelivery, OrderStates, OrderStatusHistory, UnRevisedItem, OrderComplaintReason, OrderComplaintReasonType]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationEvidenceRule.cs
    sha1: 30024b4eb2ac
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationQuestion.cs
    sha1: 0b741326b80f
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationQuestionOption.cs
    sha1: c87b209115e8
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationReason.cs
    sha1: c92e9698a208
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationRulesAuditLog.cs
    sha1: 8b9aafe317fe
  - path: Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationSettings.cs
    sha1: a53cbce648e9
  - path: Shared/TalabatkLogic/TalabatkModels/DeletedOrderDetailsItemsHistory.cs
    sha1: 10e0dd0dd3de
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryInterval.cs
    sha1: 7c76faf54370
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryInterval_Area.cs
    sha1: 18d4b1b4ce5b
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryIntervalsDescription.cs
    sha1: 9e621c4e1fba
  - path: Shared/TalabatkLogic/TalabatkModels/ItemReplacementReport.cs
    sha1: 143c8bdce79c
  - path: Shared/TalabatkLogic/TalabatkModels/OrderAgentAssignment.cs
    sha1: 24221fba4bcf
  - path: Shared/TalabatkLogic/TalabatkModels/OrderChat.cs
    sha1: 5dd890a80b76
  - path: Shared/TalabatkLogic/TalabatkModels/OrderComment.cs
    sha1: fc8b68a807c5
  - path: Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs
    sha1: 3d2416f9aed1
  - path: Shared/TalabatkLogic/TalabatkModels/OrderCostHolderRestaurant.cs
    sha1: 9933946ee54b
  - path: Shared/TalabatkLogic/TalabatkModels/OrderCountTracking.cs
    sha1: 27639a0de597
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDetailReplacement.cs
    sha1: fbdccf7b31f4
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDetailsOptions.cs
    sha1: a3f401234acd
  - path: Shared/TalabatkLogic/TalabatkModels/OrderPaymentStates.cs
    sha1: 5d6d5482ea47
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDelivery.cs
    sha1: 824d6f884a9a
  - path: Shared/TalabatkLogic/TalabatkModels/OrderStates.cs
    sha1: a9ce0e1e6b3b
  - path: Shared/TalabatkLogic/TalabatkModels/OrderStatusHistory.cs
    sha1: 536c4a140ff7
  - path: Shared/TalabatkLogic/TalabatkModels/UnRevisedItem.cs
    sha1: b5083f3358d5
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaintReason.cs
    sha1: ced7b996f69d
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaintReasonType.cs
    sha1: fe38f8000463
  - path: Shared/TalabatkApplication/Commands/ChageOrderStatustToResturantPendingCommand/ChageOrderStatustToResturantPendingCommand.cs
    sha1: cd21d4488c1b
  - path: Shared/TalabatkApplication/Commands/ChangeDeliveryManOrderStatusToDeliveredCommand/ChangeDeliveryManOrderStatusToDeliveredCommand.cs
    sha1: 6cea3a9d721c
  - path: Shared/TalabatkApplication/Commands/DeliveryManReceiveOrderCommand/DeliveryManReceiveOrderCommand.cs
    sha1: b16730f18dc5
  - path: Shared/TalabatkApplication/Commands/MakeOrderCommand/MakeOrderCommand.cs
    sha1: 8632380200e6
  - path: Shared/TalabatkApplication/Commands/RejectOrderDeliveryRequestCommand/RejectOrderDeliveryRequestCommand.cs
    sha1: 953b340f50ff
  - path: Shared/TalabatkApplication/Commands/SendPushnotificationToRestaurant/NewOrderAdded.cs
    sha1: f92d5272d8bc
  - path: Shared/TalabatkApplication/Commands/UpdateOrderCommand/UpdateOrderCommand.cs
    sha1: 1208d02f5f9e
  - path: Shared/TalabatkApplication/Helper/DailyPickupTagAssignmentExtensions.cs
    sha1: 7c9fcea24f91
  - path: Shared/TalabatkApplication/Helper/OrderCodeUniquenessExtensions.cs
    sha1: 922a0f33e0fb
  - path: Shared/TalabatkApplication/OrderBuilder/BuilderDirector.cs
    sha1: 7104af9dee60
  - path: Shared/TalabatkApplication/OrderBuilder/OrderBuilder.cs
    sha1: fcdc8279337d
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
last_updated: 2026-08-23
tags: [flow, technical]
---
# Order Lifecycle — Technical

> Bridges to [[Order.technical|Order]] (entity-level rules), [[OrderRestaurantDetails|OrderRestaurantDetails]]
> ("Portion"), [[OrderDetails.technical|OrderDetails]], and
> [[OrderDelivery.technical|OrderDelivery]] (financial/status detail on the
> delivery-man side). This note is the missing piece: the order things happen in, end to end, from
> cart confirmation to a terminal state.

## Trigger

Two live, parallel entry points create an `Order` — this note traces the first in full; the second is
bridged, not re-traced:

1. **`POST Cart/CheckOut_V1`** (`TalabatkAPIs/Controllers/Cart/CartController.cs:261,270`) →
   `CreateOrderFromCartCommand` → `Order.CreateOrderFromCustomerCart` (`Order.cs:2070+`). Newer,
   cart-based; already covered by [[Order.technical|Order]]'s gap-closure pass and
   [[Checkout-Payment-Processing|Checkout Payment Processing]] — **not re-traced**.
2. **`POST Order/MakeOrder`** (`TalabatkAPIs/Controllers/Order/OrderController.cs:475,482`) →
   `MakeOrderCommand` — legacy, item-list-based (`OrderPostDto`), still reachable (version-gated per
   [[Order.technical|Order]]'s `Version` field). **Traced step-by-step below**, per the assigned
   start points.

## Step-by-step (`MakeOrderCommand`)

1. Log the command; resolve local `nowDate` (`MakeOrderCommand.cs:123-129`).
2. Load reference data: `Configuration`, cities, restaurants (+area/hours/busy-windows), menu items,
   prices, active offers, options, delivery interval (`:138-206`).
3. Load `customerAddress` only if `command.UserAdressId.HasValue` — else it stays `null` (`:219-221`).
4. **`#352`** — the next line dereferences it unconditionally:
   `supportedAreaIds.Contains(customerAddress.AreaId.Value)` (`:226`). Any order with no `UserAdressId`
   (pickup order, or an omitting client) throws `NullReferenceException` here instead of a handled
   validation failure — on the highest-traffic write path in the system.
5. Rush-time area check, promo-code lookup/usage-limit checks, tiered-discount lookup scoped to the
   customer's segments and the order's restaurants (`:230-320`).
6. First-order/duplicate-order/mart-quantity checks, incl. `CheckMartQuantity` (`:505-517`).
7. **Order construction**: `builderDirector.CompleteOrderBuilder` (`BuilderDirector.cs:27-129`) →
   `orderBuilder.BuildOrder` (`OrderBuilder.cs:18-121`) → `Order.Instance` factory (`Order.cs:1550`):
   builds payments, delivery fees (`CalculateDeliveryFees`, `:1658-1663`), totals and profit split —
   **pricing formulas out of scope for this status-transition flow, not traced**. Calls
   `InitializeOrderStatus(configuration, isShourtCut: false, nowdate, ...)` (`:1631-1635`, body at
   `:2408-2432`) — the auto-approve gate: first order, any online payment, a duplicate order at the
   same restaurant, more than one restaurant, or total ≥ `EightOrderPendingAmount` (and not
   shortcut-app) → `StatusId=Pending` + `RestaurantOrderStatus.New` on every portion; else →
   `StatusId=RestaurantPending` + `RestaurantOrderStatus.Pending` + `RestaurantPendingTime=now`. Fires
   `AddSendNotificationsEvent`/`AddCalculateDeliveryTimeEvent`/`AddCalculateDeliveryMethodEvent`
   (`:1691-1693`).
   - **Resolves an open question in [[Order.technical|Order]]**: whether `InitializeOrderStatus`
     is dead code beside `CreateOrderFromCustomerCart`'s inline duplicate. It is not —
     `Order.Instance` calls it directly (`:1631`), while `CreateOrderFromCustomerCart` (`CheckOut_V1`)
     uses its own inline copy (`Order.cs:2107-2122`). Two live call sites, not one live and one dead.
   - **New observation, not previously logged**: `MakeOrderCommand.cs:545` passes the literal
     `isShortCutApp: false` into `CompleteOrderBuilder` regardless of `command.IsShourtCutApp`, and
     `BuilderDirector.CompleteOrderBuilder`'s own `isShortCutApp` parameter (`:53`) is never forwarded
     into `OrderBuilder.BuildOrder`/`Order.Instance` (no such parameter in its ~50-arg signature) —
     silently dropped, so `InitializeOrderStatus` always runs `isShourtCut=false` here, while
     `CreateOrderFromCustomerCart` honors a real `isShourtCutApp` in the identical condition
     (`Order.cs:2112`). The "skip the pending gate" exemption for shortcut-app customers can therefore
     never apply via the legacy `MakeOrder` route, only via `CheckOut_V1` — not confirmed whether
     shortcut-app clients still use the legacy route.
8. Wallet-balance re-check (`:552-566`); online-payment amount re-verified against a configured
   tolerance (`:570-577`) — mirrors Rule 1 in [[Order.technical|Order]].
9. **Order-code allocation**: `ctx.EnsureUniqueOrderCodeAsync(sourceOrder)` (`:584`) —
   `OrderCodeUniquenessExtensions.cs:16-23` loops `RegenerateOrderCode()` until unique.
10. **Pickup-tag allocation**: `sourceOrder.EnsurePickupTagsAsync(...)` (`:586`) —
    `DailyPickupTagAssignmentExtensions.cs:16-33` calls `IDailyPickupTagAllocator.AllocateAsync(CityId,
    orderDate)` per `OrderRestaurantDetails` ("Portion"), stamping `PickupTag`; silently skipped with
    no `CityId`. Allocator internals not opened.
11. **First DB write**: `ctx.Order.AddAsync` + `SaveChangesAsyncWithResult()` (`:588-590`) — checked,
    returns `"Un-Handled Error"` on failure. Persists `Order`+`OrderDetails`+`OrderRestaurantDetails`+
    `OrderPayments` together.
12. If landed in `RestaurantPending` with no pending online payment and not the customer's first order:
    publish `NewOrderAdded(orderId)` (`:596-599`) → `SendPushNotificationToRestaurantHandler`
    (`NewOrderAdded.cs:37-60`) pushes "New order" to the restaurants' vendor-app users.
13. `ctx.UpdateOrderWithRelativeValues(orderId)` (`:604`) — raw stored-procedure refresh, not opened.
14. If an online payment is pending and ≥ the configured minimum (`:619-624`): non-PayMob path creates
    a checkout session and calls a **second, unchecked `SaveChangesAsyncWithResult()` at `:635`** —
    same shape as the #396 family (`_conflicts.md` #63/#68/#69/#71/#72), cited in
    [[Order.technical|Order]] Rule 3; PayMob path (card/wallet) registers the PayMob order id via
    a plain, also-unchecked `SaveChangesAsync()` (`:682-683`).
15. Guard: PayMob-wallet requested but no redirect URL produced → validation failure (`:691-699`).
16. Return `CQRSResponse{Success=true, Value=redirectPaymentUrl}` (empty for pure cash/wallet orders).

**Business outcome:** order exists with `StatusId ∈ {Pending, RestaurantPending}`, `OrderCode`,
`PickupTag` per portion, and — for online orders — a payment session under way.

## Pending-gate resolution (manual only)

`Pending` has **no automated path forward** — no Hangfire/timeout job scanning `OrderStatus.Pending`
was found (contrast the `RestaurantPending` jobs below). Two admin actions can move it:
`ConfirmOrderCommand` (`:27-66`) → `order.ConfirmByAdmin(...)` (`:47`, body not opened) → straight to
`Confirmed`; or `ChangeOrderStatusToRestaurantPendingCommand`
(`ChageOrderStatustToResturantPendingCommand.cs:26-49`) → `ChangeStatusToRestaurantPending(...)` →
`RestaurantPending` — **cited bug** ([[Order.technical|Order]] Rule 3): `saveResult` captured but
never checked (`:46-47`), always returns `Result.Success()`.

**Stuck state #1:** an order nobody reviews stays `Pending` indefinitely.

## Restaurant acceptance window (`RestaurantPending`)

`RestaurantPendingRoboCallsJob` (`AdminUi/Helper/HangFire/Jobs/RestaurantPendingRoboCallsJob.cs:103-104`) and
`RestaurantRoboCallCheckJob` (`Shared/TalabatkApplication/Helper/HangFire/RestaurantRoboCallCheckJob.cs:44-49`) scan orders where
`StatusId==RestaurantPending` and a portion is `RestaurantOrderStatus.Pending`, and robocall the
restaurant. **They nag; they do not change status, cancel, or reassign.**

**Stuck state #2:** an unresponsive restaurant leaves the order in `RestaurantPending` indefinitely —
only a human action (confirm/reject, or admin override via
`RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand`) advances it.

- **Confirm** (per restaurant): `ConfirmOrderRestaurantCommand.Handle` (`:38-91`) →
  `order.ConfirmRestaurantOrderDetails` (`Order.cs:3886-3968`) — validates the portion is
  `Pending`/`RestaurantView` (fails if already confirmed/rejected/hold, or order is
  `Rejected`/`Delivered`/`OnWay`); marks `OrderDetails.RestaurantConfirmed=true`; **once every
  restaurant has confirmed**: sets `CookingTime`, `StatusId=Confirmed`, `ResponseDate`, fires
  `RequestNewDeliveryManAEvent` (`:3951` — kicks off driver assignment), `AddOrderStatusNotificationEvent`,
  `AddLogisticsRushOrderEvent`, `NotifyRestaurantToStartCookingEvent` (`:3959`); single-restaurant
  non-delayed orders auto-mark start-cooking immediately. Save checked (`:86`).
  `AutoConfirmOrderAfterBlockingMerchantsRemoved` (`:3993-4030`) applies the same transition when a
  previously-blocking merchant's rejection clears and every remaining portion is confirmed.
- **Reject** (whole/partial): `RejectRestaurantOrderOverallCommand.Handle` (`:66-280`) — validates
  reason + restaurant-in-order + portion status; full rejection (`:189`) triggers
  `_onlinePaymentRefundService.ApplyBankRefundAfterRejectIfNeededAsync` (`:204`); partial rejection
  recalculates the order via `RemoveUnavailableItems` (`:222`, re-runs discount/promo/offers/fees).
  Admin equivalents `RejectOrderFromAdminCommand`/`RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand`
  share the shape but have a **cited bug**: unguarded `OrderRejectedReason` dereference
  ([[Order.technical|Order]], "Order-rejection family"). Terminal: `StatusId=Rejected`.

## Cooking → ready to pick up

- `RestaurantStartCookingCommand.Handle` (`:35-91`): requires every portion already
  `Confirmed`/`Cooking` (`:53-57`), marks the named portion `StartCooking`. **Cited bug**: `.Find(...)`
  (`:65`) and the following `.FirstOrDefault(...)` (`:75`) are unguarded — an unrelated `RestaurantId`
  throws `NullReferenceException`.
- `ConfirmResturantReadyToPickupOrderCommand.Handle` (`:37-70`) → `order.OnReadyToPickup(...)` (`:58`);
  `ValidateOrderStatus` (`:76-108`) rejects if still `RestaurantPending`/already `OnWay`, if the portion
  is already `ReadyToPickUp`/`PickedUp`, and enforces a minimum-elapsed-cooking-time check. **Cited
  bug**: the cooking-time check (`:99`) dereferences `restaurantDetails.CookingTime` unguarded, unlike
  the two `?.`-guarded checks just above it — an unknown `restaurantId` throws instead of falling
  through ([[Order.technical|Order]]).

## Driver assignment

Triggered by `RequestNewDeliveryManAEvent` fired inside `ConfirmRestaurantOrderDetails` at `Confirmed`.
Round-robin/force-assign machinery (`RoundRobinService`, `ForceAssignDeliverymenService`,
[[Delivery-Assignment-Strategies|Delivery Assignment Strategies]]) not traced in depth;
two pre-existing defects sit on this step: **`#260`** — `RoundRobinService.AssignOrderToUserInRound`
reads the highest-weight agent outside any lock, only the decrement is locked — a read-then-decrement
race that can skew fairness or double-route under concurrency. **`#272`** —
`ForceAssignDeliverymenService` fires cache/queue calls without `await` inside `Parallel.ForEach`/async
methods — exceptions from a queue add/remove can be silently lost.

A driver accepts (`ApproveOrderDeliveryRequestCommand`) or declines
(`RejectOrderDeliveryRequestCommand.cs:31-61`, idempotent at `:42-44`) an assignment.
`OrderDeliveryStatus` moves `Initialize→New` (accepted), `→RequestRejected` (declined), or `→Timeout`
if unanswered. `AssignOrderToDeliveryMan` (`Order.cs:3467+`) sets `StatusId=AssignDeliveryManDate` or
`DeliveryManViewed` depending on admin-vs-driver origin — body not traced further.

**Stuck state #3 (unconfirmed):** whether a `Timeout`ed request reliably triggers reassignment, and
whether that path can itself silently fail per `#272`, was not traced.

## Driver views → picks up → on the way → delivered

- **Viewed**: `ChangeOrderStatusCommand`'s `DeliveryManViewed` branch (`:172-175`) or the parallel
  `ChangeOrderStatusToDeliveryManViewCommand` — two independent implementations of the same
  transition, same controller; which the client actually calls was not confirmed.
- **Picked up**: `DeliveryManReceiveOrderCommand.Handle` (`:54-159`) →
  `MarkRestaurantDetailsAsRecievedFromDeliveryMan` (`:94-99`, body not traced) — GPS-distance-validates
  against the restaurant (unless on the no-validation allow-list), marks the portion `PickedUp`.
  Optional pickup photo: **`#419` (3rd instance)** — old `DeliveryManPickupImage` deleted (`:127`)
  before the new upload (`:141`)/save (`:155`) are confirmed.
- **On the way** (per driver/portion): `ChangeOrderDeliveryStatusToOnWayCommand.Handle` (`:47-160`) —
  requires `IsPrimary` (`:89`), all portions `PickedUp`, no unaccepted supporter request; stamps
  `RecordOnWayDate` (`:123`); once every primary `OrderDelivery` is on-way (`:127-131`), sets order-level
  `ChangeOrderOnWayDate` (`:134`, `StatusId=OnWay`) and notifies all assigned drivers. Save checked
  (`:137-140`). Admin equivalent `ChangeOrderStatusToOnWayCommand` has a **cited bug**: dereferences
  `order.DeliveryManId` before the `order==null` check. The generic `ChangeOrderStatusCommand`'s own
  `OnWay` branch (`:99-113,224-233`) independently re-implements the same "all portions `PickedUp`"
  gate — duplicated, not shared.
- **Delivered** (terminal): `ChangeDeliveryManOrderStatusToDeliveredCommand.Handle` (`:67-183`) —
  confirms driver ownership; non-external orders are GPS-distance-validated against
  `DeliveryLocation` (`AvalibleCustomerDisanceInMeter=500m`, `:102`); loads `Customer` and **correctly
  guards** `customer==null` (`:112`, unlike the sibling `ChangeOrderStatusCommand`'s unguarded lookup
  on the same table, cited in [[Order.technical|Order]] Rule 3); calls
  `order.DeliveryManDeliverOrder(...)` (`:121`, `Order.cs:3405-3434`), which sets `StatusId=Delivered`
  **even for a failed/returned delivery** — the only differentiator is
  `IsNotDelivered`/`NotDeliveredReasonId`; completes each `OrderDelivery` (cash/profit reconciliation,
  see [[OrderDelivery.technical|OrderDelivery]] Rule 1); fires
  loyalty/first-order-bonus/shift-bonus events only when actually delivered. Optional delivery-proof
  photo: **`#419` (1st, headline instance)** — old `CustomerDeliveryImage` deleted (`:163`) before the
  new photo is uploaded (`:168`) and the order saved (`:178`) — a failed upload leaves the DB pointing
  at a now-deleted dispute-evidence file with no recovery. Final save checked (`:178-181`).

## Cancellation (customer-initiated, early only)

Bridged from [[Order.technical|Order]] Rule 3, not re-traced: `CancelOrderCommand` blocks
cancellation once the restaurant has confirmed, ownership-checked. Sibling `CancelPaymentCommand` has
the same guard but both rejection branches return `Success=true` regardless — a caller branching on
`Success` alone treats a blocked cancellation as a success (same shape as the `#396` family, though not
itself a numbered register entry).

## Data written

`Order`+`OrderDetails`+`OrderRestaurantDetails`+`OrderPayments` created together
(`MakeOrderCommand.cs:588-590`); `Order.OrderCode` mutated pre-insert by `EnsureUniqueOrderCodeAsync`;
`OrderRestaurantDetails.PickupTag` stamped in the same transaction; PayMob/session fields mutated
post-save (`:635`,`:682-683`, both under-checked); `OrderDetails.RestaurantConfirmed`,
`RestaurantOrderStatus`, `Order.StatusId`/`CookingTime`/`ResponseDate` mutated by each
confirm/reject/cooking/ready command (one save per command); `OrderDelivery` on-way/completion fields
and `DeliveryMen` wallet/cash rows via the on-way/delivered commands (see
[[OrderDelivery.technical|OrderDelivery]]); `CustomerDeliveryImage`/
`DeliveryManPickupImage` file+DB pointer pairs, written in the unsafe order flagged by `#419`;
`WalletTransaction` (first-order referral bonus) added inside `ChangeOrderStatusCommand`'s `Delivered`
branch (`:139-149`), not inside `DeliveryManDeliverOrder` itself.

## External calls

`IDailyPickupTagAllocator.AllocateAsync` (per-city daily counter, internals not traced);
`ICheckoutCreateSession`/`IPayMobProviderServices` (online payment session, see
[[PayMob.technical|PayMob]]); `ctx.UpdateOrderWithRelativeValues` (raw stored
procedure, not traced); `IOnlinePaymentRefundService.ApplyBankRefundAfterRejectIfNeededAsync` (not
traced beyond the call site); push notifications via `IVendorAppNotificationProvider` (new order →
restaurant) and `IAndroidGCMPushNotification` (on-way/delivered → drivers; transport not traced);
robocall jobs (`RestaurantPendingRoboCallsJob`, `RestaurantRoboCallCheckJob`, outbound provider not
traced).

## Failure modes

- **`#352`** — `MakeOrderCommand.cs:226` (and `UpdateOrderCommand.cs:582-589`) — unguarded
  `customerAddress.AreaId.Value`; NRE with no address id.
- **Unregistered, `#396`-shaped** — `MakeOrderCommand.cs:635` online-payment-session save, result
  discarded, success reported regardless.
- **`#419`** — three instances on this flow: delivered-photo (`ChangeDeliveryManOrderStatusToDeliveredCommand.cs:163-178`),
  pickup-photo (`DeliveryManReceiveOrderCommand.cs:127-155`), and the nightly
  `CleanupDeliveryImagesJob` deleting image folders before the nulling transaction commits.
- **`#260`** — round-robin race, can misassign under concurrent orders.
- **`#272`** — force-assign queue operations can silently no-op on exception.
- Each restaurant-side command (`ChangeOrderStatusToRestaurantPendingCommand`,
  `RestaurantStartCookingCommand`, `ConfirmResturantReadyToPickupOrderCommand`,
  `ChangeOrderStatusToOnWayCommand`, `ChangeOrderStatusCommand`'s `Delivered` branch) has its own
  already-cited unguarded-lookup or discarded-save bug — full list in
  [[Order.technical|Order]] Rule 3; repeated here only where it lands on a lifecycle step.
- **Stuck states**: `Pending` with no admin action (#1); `RestaurantPending` with no restaurant action
  (#2, robocalls only nag); a `Timeout`ed assignment whose reassignment silently fails (#3, unconfirmed).

## Folded entities — the 26 satellites documented here

Every entity this note covers, what it is, and its real rules. They divide cleanly into three groups,
and the division is itself the useful fact: the **auto-compensation** set is the most rigorously
validated code in the order domain, the **order satellites** have almost no validation at all, and the
**lookups** have none by design.

### Auto-compensation — the exception, not the rule

Six entities added later than the rest, and they behave like a different codebase: private
constructors, `Create`/`Update` returning `Result`, an audit trail, and guards on both the create and
the update path with **identical messages** on each.

| Entity | What it is | Rules |
|---|---|---|
| `AutoCompensationReason` | A reason a customer may be auto-compensated, with a default liability party and value | `Create` requires an Arabic name and a creator (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationReason.cs:57`, `:60`); `Update` requires the same plus a modifier (`:96`, `:99`); `SetActive` and `UpdateDisplayOrder` each require a modifier (`:115`, `:126`). Two business invariants beyond field checks: the **operator can never be the default liability party** (`:137`), and a non-item-linked reason **must** carry a default compensation value (`:148`) |
| `AutoCompensationEvidenceRule` | How much photo evidence a reason requires | Rejects a negative photo count (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationEvidenceRule.cs:67`) and — the interesting one — rejects a count of **zero when evidence is required** (`:70`), so "evidence required, no photos" cannot be stored |
| `AutoCompensationQuestion` | A question asked of the customer for a reason | Requires Arabic text and an actor on create and update (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationQuestion.cs:44-47`, `:77-80`). Enforces the option-count rule for options-type questions — **at least two** (`:125`) and **at most three** (`:128`) — and forbids options on free-text questions (`:148`). The only entity in the order domain that validates a child collection's shape |
| `AutoCompensationQuestionOption` | One selectable answer | Requires Arabic text and a creator (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationQuestionOption.cs:27`, `:30`) |
| `AutoCompensationSettings` | The singleton settings row | `CreateInitial` seeds it; `Touch` stamps who changed it and requires a name (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationSettings.cs:26`) |
| `AutoCompensationRulesAuditLog` | Who changed which rule, when, and a summary | `Create` only, no guards (`Shared/TalabatkLogic/TalabatkModels/AutoCompensation/AutoCompensationRulesAuditLog.cs:17`) — appropriate for an append-only log, and the only audit trail any of these 26 entities has |

Arabic text is required on all four; **English text is optional on every one of them**. So an
auto-compensation flow can be Arabic-only, and nothing objects.

### Order satellites — rows the lifecycle writes

| Entity | What it is | Rules |
|---|---|---|
| `OrderStatusHistory` | One status transition, who caused it, and whether it was a non-delivery | Private ctor, `Instance` only, **no validation** (`Shared/TalabatkLogic/TalabatkModels/OrderStatusHistory.cs:26`). This is the audit trail the whole status flow depends on, and nothing enforces that the status is a real one |
| `OrderComment` | A free-text note against an order, tagged with the status and action it was made under | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/OrderComment.cs:30`) |
| `OrderAgentAssignment` | Which support agent owns an order, and why it was reassigned | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/OrderAgentAssignment.cs:14`) |
| `OrderRestaurantDelivery` | Which driver is carrying which restaurant's part of a multi-restaurant order | `Instance` plus a `SetDeliveryManId` that assigns without checking (`Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDelivery.cs:12`, `:24`) |
| `OrderDetailsOptions` | The options a customer chose on one order line, with their prices and tax | `Instance` returns `Result` but **cannot fail** (`Shared/TalabatkLogic/TalabatkModels/OrderDetailsOptions.cs:18`); `BuildCartItemOptions` (`:42`) is the cart-to-order translation, and `Update`/`UpdateExistOption` (`:80`, `:88`) return the entity rather than a `Result`. Prices and names are **copied** onto the row, so an order keeps what the customer saw |
| `OrderCostHolder` | Who absorbs the cost when an order goes wrong — driver, 8Orders, agent, or restaurants | `Instance` (`Shared/TalabatkLogic/TalabatkModels/OrderCostHolder.cs:44`) has no guards despite holding four separate deductible amounts. `AddRestaurantDeductibles` (`:77`) attaches the per-restaurant split, and `FireCostHolderCreatedEvent` (`:100`) raises the domain event the accounting side listens for |
| `OrderCostHolderRestaurant` | One restaurant's share of that deduction | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/OrderCostHolderRestaurant.cs:17`). Money with no validation, on both halves |
| `OrderChat` | The order-scoped support conversation, with its own status machine | `Instance` returns `Result` and cannot fail (`Shared/TalabatkLogic/TalabatkModels/OrderChat.cs:36`); `AddMessage` (`:51`), `AssignAgent` (`:61`), `MakeChatClosed`/`MakeChatActive`/`MakeDisconnected` (`:67`, `:72`, `:78`) — five transitions, **no guard on any of them**, so any state can follow any other |
| `OrderDetailReplacement` | A replacement item chosen for an order line | `Create` only, no guards (`Shared/TalabatkLogic/TalabatkModels/OrderDetailReplacement.cs:17`) |
| `ItemReplacementReport` | A denormalised report row for one replacement request, from suggestion to outcome | 24 properties, all copied from elsewhere. `CreatePending` (`Shared/TalabatkLogic/TalabatkModels/ItemReplacementReport.cs:36`) then one `Mark*` method per outcome — replaced with a suggestion (`:78`), replaced at a different quantity (`:94`), replaced with a chosen item (`:110`), removed from the order (`:126`), or order cancelled (`:139`). No guards, but the **named-transition style makes the intent legible without them**: the state space is the method list |
| `DeletedOrderDetailsItemsHistory` | Which item was removed from which order, and when | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/DeletedOrderDetailsItemsHistory.cs:18`) |
| `OrderCountTracking` | Per-minute order counters, split food vs mart | `Instance` and `UpdateCounts`, neither validating (`Shared/TalabatkLogic/TalabatkModels/OrderCountTracking.cs:22`, `:47`). Ten counters on one row is what makes the operations dashboard cheap to read |
| `UnRevisedItem` | An ERP-imported item awaiting a human to classify it | `Instance` rejects only the case where **both** names are blank — the condition is `&&`, so an item with an Arabic name and no English name is accepted (`Shared/TalabatkLogic/TalabatkModels/UnRevisedItem.cs:59-61`, note the leading space in the message). `UpdateBrandAndCategory` (`:39`), `UpdateAction` (`:86`) and `UpdateDetails` (`:92`) are all unguarded `void` |

### Delivery intervals — scheduled delivery windows

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryInterval` | A selectable delivery window for a city, with its own cost and urgency flag | No guards anywhere. `CheckValidDates` (`Shared/TalabatkLogic/TalabatkModels/DeliveryInterval.cs:37`) returns a bare `bool` rather than a `Result`, and the three setters — `SetIsActive`, `SetFromTime`, `SetToTime` (`:63`, `:72`, `:78`) — return `Result` but never fail. So nothing prevents a window whose `ToTime` precedes its `FromTime`; `CheckValidDates` exists to detect it and is not called from the setters. Its controller is the one with **zero action methods** — 🔴 `_conflicts.md` #9 |
| `DeliveryInterval_Area` | Which areas an interval is offered in | Five properties, **no methods** (`Shared/TalabatkLogic/TalabatkModels/DeliveryInterval_Area.cs`) |
| `DeliveryIntervalsDescription` | An interval's name in one language | Six properties and a `ToString` (`Shared/TalabatkLogic/TalabatkModels/DeliveryIntervalsDescription.cs:19`) — no factory, so rows are built by EF or the caller |

### Complaint reasons and status lookups

| Entity | What it is | Rules |
|---|---|---|
| `OrderComplaintReason` | A reason a customer may complain, weighted for merchant scoring | The one entity here with a **public static validator separate from its factory**: `ValidateWeight` (`Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaintReason.cs:43`) is called by `AddReasonCommand` and `EditReasonCommand` *before* construction, while `Instance` (`:17`) and `Edit` (`:34`) themselves guard nothing. Its failure message is **Arabic-only**, inside the domain layer (`:46`) — another instance of 🔴 `_conflicts.md` #621. Soft-deleted via `Delete` (`:51`) |
| `OrderComplaintReasonType` | The grouping above a complaint reason | Three properties, no methods (`Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaintReasonType.cs`) |
| `OrderStates` | The order-status lookup table, with Arabic and English names | Five properties, no methods (`Shared/TalabatkLogic/TalabatkModels/OrderStates.cs`). Behaviour comes from the `OrderStatus` enum, not this table — the same table-versus-enum coupling recorded for [[Admin/Order & Customer Administration/PaymentMethod\|PaymentMethod]] in 🟡 #632 |
| `OrderPaymentStates` | The payment-status lookup table | Three properties, no methods (`Shared/TalabatkLogic/TalabatkModels/OrderPaymentStates.cs`). Its ids must match `OrderPaymentStatus`, whose value 3 collides with `PaymentMethods.Online` — 🔴 #631 |

### What the split means

Twenty of these 26 entities have **no validation of any kind**, including every one that carries money
(`OrderCostHolder`, `OrderCostHolderRestaurant`, `OrderDetailsOptions`) and the one that records the
status trail the whole lifecycle depends on (`OrderStatusHistory`). The six auto-compensation entities,
written later, guard everything and keep an audit log. The order domain therefore has two standards in
one folder, and which one applies depends on when the code was written rather than on what it does.

## Open Questions

- [ ] Should `OrderChat`'s five transitions guard the state they move from? Any transition can follow any
      other today.
- [ ] `DeliveryInterval.CheckValidDates` exists but is not called by the setters that could produce an
      invalid window. Is it used anywhere, or is the check dead?
- [ ] `UnRevisedItem.Instance` accepts an item with only one language's name (`&&`, not `||`). Which does
      the customer app show when the other is missing?
- [ ] Auto-compensation requires Arabic text and leaves English optional on all four text-bearing
      entities. Is an Arabic-only compensation flow intended?
- [ ] Whether shortcut-app clients still reach the legacy `MakeOrder` route (not registered in
  `_conflicts.md`); `Order.ConfirmByAdmin`/`AssignOrderToDeliveryMan`/
  `MarkRestaurantDetailsAsRecievedFromDeliveryMan` bodies (call sites confirmed, internals not traced);
  whether `OrderDeliveryStatus.Timeout` reliably triggers reassignment and whether that path can itself
  silently fail per `#272`.
- [ ] `ChangeOrderStatusToDeliveryManViewCommand` vs `ChangeOrderStatusCommand`'s `DeliveryManViewed`
  branch — which app version calls which, whether they can disagree; `RoundRobinService`/
  `ForceAssignDeliverymenService` internals beyond `#260`/`#272` — not opened.
- [ ] `CreateOrderFromCartCommand` (`CheckOut_V1`) step-by-step intentionally not re-traced — bridged
  via [[Order.technical|Order]] and
  [[Checkout-Payment-Processing|Checkout Payment Processing]]; delivery-fee
  calculation (`Order.CalculateDeliveryFees`, `Order.cs:1658`) out of scope for this status-transition
  flow, not traced.
