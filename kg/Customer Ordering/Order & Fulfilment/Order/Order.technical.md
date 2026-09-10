---
id: 8orders/customer-ordering/order-and-fulfilment/order-technical
note_type: technical
rule_count: 4
context: Customer Ordering
feature: Order & Fulfilment
entity: Order
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/CalculateItemsReplacementTotalCommand/CalculateItemsReplacementTotalCommand.cs
    sha1: 094bc548ce3c
  - path: Shared/TalabatkApplication/Commands/CancelOrderCommand/CancelOrderCommand.cs
    sha1: 1959b7a4f8c3
  - path: Shared/TalabatkApplication/Commands/CancelPaymentCommand/CancelPaymentCommand.cs
    sha1: 93c43e7ebf8c
  - path: Shared/TalabatkApplication/Commands/ChageOrderStatustToResturantPendingCommand/ChageOrderStatustToResturantPendingCommand.cs
    sha1: cd21d4488c1b
  - path: Shared/TalabatkApplication/Commands/ChangeOrderStatusCommand/ChangeOrderStatusCommand.cs
    sha1: 95f0af9825b4
  - path: Shared/TalabatkApplication/Commands/ChangeOrderStatusToOnWayCommand/ChangeOrderStatusToOnWayCommand.cs
    sha1: d595277da986
  - path: Shared/TalabatkApplication/Commands/ConfirmRestuarntReadyToPickupOrderCommand/ConfirmResturantReadyToPickupOrderCommand.cs
    sha1: 5d64a96d9ac4
  - path: Shared/TalabatkApplication/Commands/GetOrderTimeLineQuery/GetOrderTimeLineQuery.cs
    sha1: b6465315568f
  - path: Shared/TalabatkApplication/Commands/MakeOrderCommand/MakeOrderCommand.cs
    sha1: 8632380200e6
  - path: Shared/TalabatkApplication/Commands/NotifyCustomerToReplaceItemsCommand/NotifyCustomerToReplaceItemsCommand.cs
    sha1: 19c95ee1fbea
  - path: Shared/TalabatkApplication/Commands/NotifyCustomerToReplaceItemsCommand/ReplacementItemCreator.cs
    sha1: c3d5bf1a90ad
  - path: Shared/TalabatkApplication/Commands/ProceedFirstCustomerOrderCommand/ProceedFirstCustomerOrderCommand.cs
    sha1: 24a3896c6091
  - path: Shared/TalabatkApplication/Commands/RegenerateURLCommand/RegenerateURLCommand.cs
    sha1: 04de9458b503
  - path: Shared/TalabatkApplication/Commands/RejectOrderFromAdminCommand/RejectOrderFromAdminCommand.cs
    sha1: a8d836d1ebdf
  - path: Shared/TalabatkApplication/Commands/RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand/RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand.cs
    sha1: 86480cdac1f7
  - path: Shared/TalabatkApplication/Commands/RejectRestaurantItemsCommand/RejectRestaurantItemsCommand.cs
    sha1: 00c25b3ac2e9
  - path: Shared/TalabatkApplication/Commands/RejectSomeItemsResturantCommand/RejectSomeItemsResturantCommand.cs
    sha1: 006a31cea7ca
  - path: Shared/TalabatkApplication/Commands/RestaurantStartCookingCommand/RestaurantStartCookingCommand.cs
    sha1: 674e1ff37cca
  - path: Shared/TalabatkApplication/Commands/SendTawkToNotificationToCustomerCommand/SendTawkToNotificationToCustomerCommand.cs
    sha1: 2aeee5d0bccf
  - path: Shared/TalabatkApplication/Commands/UpdateOrderByOrderCodeCommand/UpdateOrderByOrderCodeCommand.cs
    sha1: aa2967f1885c
  - path: Shared/TalabatkApplication/Commands/UpdateOrderCommand/UpdateOrderCommand.cs
    sha1: 1208d02f5f9e
  - path: Shared/TalabatkLogic/Enum/OrderStatus.cs
    sha1: 15428f36a3f6
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: TalabatkAPIs/Controllers/Deliveryintevral/DeliveryIntervalController.cs
    sha1: bc6bfacf4138
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, transactional, technical, backend-domain]
---
# Order — Technical (Customer Ordering slice only — see scope note)

> **Layer:** Domain — Legacy POCO, event-raising   **Context:** Customer Ordering (this note) / Delivery / Restaurant Portal / Admin (not covered here)   **Feature:** Order & Fulfilment
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Order.cs`   **Last Updated:** 2026-08-02

> ⚠️ **SCOPE NOTE — this is the single biggest entity in the codebase, and this note is
> deliberately partial.** `Order.cs` is **6,235 lines** with **60+ public methods**, covering
> delivery-man assignment/swap/distance-validation, restaurant confirmation/rejection/cooking
> status, compensation, ERP sync, delivery images, and admin-viewed tracking — none of which is
> Customer Ordering's concern. This note covers **only** the slice a Customer Ordering pass should
> own: order creation from cart, payment-method rules, the pending/auto-approve gate, and
> cancellation. The Delivery, Restaurant Portal, and Admin slices of `Order` should be documented
> when those contexts get their own knowledge-graph pass — **do not assume this note is complete
> for `Order` as a whole.**

## Business Rules (Customer Ordering slice)

### Rule 1: Payment methods — cash and online are mutually exclusive; wallet can combine with either
- **Source:** `Order.cs:2291-2376` (`AddOrderPayments`) — at least one of cash/wallet/online must be
  selected; cash + online together is rejected outright
  (`"Cash payment cannot be combined with online payment."`). Wallet-only requires the wallet
  balance to cover the full order total. Wallet amount used is capped at
  `Math.Min(customerWalletBalance, Total)` — never more than the order needs.
- **Online payment amount is re-verified server-side**, not trusted from the client: the expected
  online amount is computed from `Total + tips - wallet`, compared against what was sent, and
  rejected if the difference exceeds a configured tolerance
  (`Order.cs:2393-2405`, `"Total Online Payment is Not Correct"`).
- A minimum online-payment amount is also enforced (`Order.cs:2367-2370`).

### Rule 2: New orders start in one of two states — an auto-approve gate based on risk signals
- **Plain language:** A cash order from a repeat customer, at a single restaurant, below a
  configured amount threshold, skips a manual pending/review step and goes straight to
  "restaurant pending" (effectively auto-approved to the restaurant). Anything riskier requires the
  extra `Pending` gate first.
- **Trigger conditions that force the `Pending` gate** (any one is enough): it's the customer's
  first order ever, any online payment is involved, it's an Apple Pay order, the customer already
  has a duplicate/open order at the same restaurant, the order spans more than one restaurant, or
  the order total is at/above a configured threshold (`EightOrderPendingAmount`) **and** it's not
  the "shortcut app" channel.
- **Source:** `Order.cs:2078-2094` (`CreateOrderFromCustomerCart`), mirrored in
  `Order.cs:2410-2438` (`InitializeOrderStatus`, a second code path with the same condition set —
  confirm the two stay in sync if this rule ever changes, see Open Questions).
- Statuses involved: `Pending` (1) with `RestaurantOrderStatus.New`, or `RestaurantPending` (12)
  with `RestaurantOrderStatus.Pending` and a timestamp (`RestaurantPendingTime`).

### Rule 3: Cancellation is blocked once the restaurant has confirmed
- **Plain language:** A customer can only cancel their own order while it's still early —
  rejecting/cancelling after the restaurant has already confirmed it is not allowed through this
  path.
- **Source:** `Shared/TalabatkApplication/Commands/CancelOrderCommand/CancelOrderCommand.cs:71-90` —
  order must exist, must belong to the requesting customer (`"Unauthorized"` otherwise), must not
  already be rejected, and must not already be past confirmation
  (localized `rejectAfterConfirmation` message).
- **⚠️ Confirmed bug, sibling command `CancelPaymentCommand`:** the same "reject after confirmation"
  guard exists here too, but on **both** rejection branches (`order not found`, and `already past
  confirmation`) the handler returns `CQRSResponse { Success = true, ErrorMessage = "..." }` —
  `Success` is `true` even though the cancellation did **not** happen. A caller that branches on
  `Success` alone (as `_conflicts.md` #56 shows callers sometimes do) would treat a blocked
  cancellation as if it succeeded.
  **Source:** `CancelPaymentCommand.cs:85-89`.
- **⚠️ Confirmed bug (grep-swept pattern), `MakeOrderCommand`/`RejectRestaurantItemsCommand`:** both
  have a `SaveChangesAsyncWithResult()` call whose result is never checked before the method reports
  success — `MakeOrderCommand.cs:635` (the secondary save that persists the PayMob payment indicator,
  after the primary order-creation save at `:590` is correctly checked) and
  `RejectRestaurantItemsCommand.cs:117` (the **only** save in the handler — a restaurant "reject
  items" action that always reports `Success = true` at `:133` regardless of whether the rejection
  actually persisted). See `_conflicts.md` #72 for the full grep-swept list.
- **⚠️ Confirmed bug, `GetOrderTimeLineQuery`:** `orderdata` from `FirstOrDefaultAsync` (`:31-54`) is
  dereferenced at `:60` with no null-check — an invalid `OrderId` throws `NullReferenceException`
  instead of a graceful failure. Same recurring unguarded-null-after-lookup shape as #58/#59/#65/#66/#67/#82.
  **Source:** `GetOrderTimeLineQuery.cs:31-60`.
- **⚠️ Confirmed bug, `ConfirmResturantReadyToPickupOrderCommand.ValidateOrderStatus`:** the first two
  checks correctly use `restaurantDetails?.RestaurantOrderStatus` (null-conditional, `:90,95`), but the
  very next check dereferences `restaurantDetails.CookingTime` directly with no `?.` (`:99`) — if the
  restaurant isn't found in the order's `OrderRestaurantDetails` (`Find` returns null), this throws
  `NullReferenceException` instead of falling through gracefully like the two checks right above it.
  **Source:** `ConfirmResturantReadyToPickupOrderCommand.cs:88-99`.
- **⚠️ Confirmed bug, `ChangeOrderStatusToOnWayCommand`:** fetches `order` via `FirstOrDefaultAsync`,
  then immediately dereferences `order.DeliveryManId` to look up the delivery man (`:38-40`) —
  **before** the `if (order == null)` check that follows right after it (`:42-45`). An invalid
  `OrderId` throws `NullReferenceException` instead of reaching the intended "Order can't be found"
  failure.
  **Source:** `ChangeOrderStatusToOnWayCommand.cs:28-45`.
- **⚠️ Confirmed bug, `ChangeOrderStatusCommand`:** in the `Delivered` branch, `customer` (fetched via
  `FirstOrDefaultAsync`, not guaranteed non-null) is dereferenced directly —
  `customer.TA_CustomerReference` — with no null-check, unlike the `culture` line just above it in the
  same method which correctly uses `customer?.PreferredLanguage`. An order whose `CustomerId` doesn't
  resolve to a `Customer` row would throw `NullReferenceException` here instead of the null-conditional
  pattern used two lines earlier.
  **Source:** `ChangeOrderStatusCommand.cs:83-133`.
- **⚠️ Confirmed bug, `ChangeOrderStatusToRestaurantPendingCommand`:** the save result is captured but
  never checked — `Handle` always `return Result.Success()` regardless of whether
  `SaveChangesAsyncWithResult()` actually succeeded, unlike every sibling status-change command in
  this pass which checks it.
  **Source:** `ChageOrderStatustToResturantPendingCommand.cs:46-47`.

### Rule 4: Order status enum (Customer Ordering-visible subset)
`Shared/TalabatkLogic/Enum/OrderStatus.cs` — `Pending(1)`, `Confirmed(2)`, `Rejected(3)`,
`OnWay(4)`, `Delivered(5)`, `AssignDeliveryManDate(6)`, `DeliveryManViewed(8)`,
`ReadytoPickup(10)`, `RestaurantRejected(11)`, `RestaurantPending(12)`, `RestaurantView(13)`,
`RestaurantNotAvilableItems(14)`, `RestaurantStartCooking(30)`. Note the gaps in numbering (7, 9,
15-29 unused) — likely removed/deprecated statuses; not investigated further in this pass. Most of
these (delivery-man/restaurant-side transitions) belong to the Delivery/Restaurant Portal slices,
not documented here.

## Key Fields (Customer Ordering-relevant subset)
| Field | Meaning |
|-------|---------|
| `CustomerId`, `CustomerName`, `CustomerMobileNumber` | Snapshotted at creation, same denormalization pattern as `CustomerCart` |
| `LockedTieredDiscountId` | Carried over from `CustomerCart.LockedTieredDiscountId` at creation |
| `DeliveryFees` / `ExtraRestaurantDeliveryFees` / `SpecialOrderDeliveryFees` | Delivery cost breakdown |
| `Total`, `TotalBeforeDiscount`, `PromoValue` | Computed order totals |
| `IsFirstCustomerOrder` | Drives the auto-approve gate (Rule 2) |
| `Version` | App version string, used elsewhere for gating legacy client behavior (see `TalabatkAPIs` version-gated routes, e.g. `AddNewCartItem_V1`) |
| `Origin` | Order source/channel |

## Status / State
See Rule 2 (initial gating) and `OrderStatus` enum (Rule 4). Full transition graph (confirm →
restaurant accepts/rejects → cooking → ready → delivery-man assigned → picked up → on way →
delivered) spans Delivery and Restaurant Portal methods not covered in this note.

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| [[CustomerCart.technical\|CustomerCart]] | Backend-Domain | `CreateOrderFromCustomerCart(cart, ...)` | Terminal step of checkout. |
| [[PromoCodes.technical\|PromoCodes]] / [[Vouchers.technical\|Vouchers]] / [[TieredDiscount.technical\|TieredDiscount]] | Backend-Domain | All three read and applied inside order-total calculation | See each entity's own checkout-time rules. |
| [[OrderRestaurantDetails\|OrderRestaurantDetails]] ("Portion") | Backend-Domain (child) | One row per restaurant in a multi-merchant order | Carries the Daily Pickup Tag (`PickupTag` field) — see `TalabatkAPIs/CONTEXT.md`. |
| Restaurant Portal, Delivery, Admin | *(not covered in this pass)* | Direct method calls on this same `Order` class | This is the single biggest cross-context coupling point in the whole system — see Open Questions. |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | very high, not counted | 60+ public methods touch this class from every context |
| Sides touched | all | Backend-Domain/Application/Data, every API host that deals with orders |
| Cross-context integrations | many, only partially documented | Restaurant Portal (confirm/reject/cook), Delivery (assign/pickup/deliver), Admin (compensation/ERP sync) |
| Domain events involved | 3+ confirmed in this pass | `AddSendNotificationsEvent`, `AddCalculateDeliveryTimeEvent`, `AddCalculateDeliveryMethodEvent` (all fired at creation, `Order.cs:2140-2142`) — likely more elsewhere in the class, not enumerated |
| Hub? | **yes — the largest hub in the system** | Every context that touches an order at all touches this one class |

## Gap-closure pass (2026-08-03): the previously-unread `OrderController` routes, mapped to their commands
The 30 routes flagged as unread are now mapped to the exact command each dispatches — closing the
"not even mapped" gap, though most command handlers' internal rules are still open for a future
deeper pass (noted per-route below where not read in full):
- `MakeOrder` → `MakeOrderCommand` — a large, ~35-field command mirroring most of `Order`'s
  create-time fields (cash/wallet/online split, promo code, delivery interval, tips, PayMob/Apple Pay
  flags, customer card). Not read in full — the actual validation/creation logic is inside the
  handler, not traced in this pass.
- `UpdateOrder` → `UpdateOrderCommand` — an even larger admin-style full-field update (restaurant
  contact info, status name, payment state, timestamps for every stage) — reads like a back-office
  edit surface reachable through the customer-facing host, not traced further.
- `ChangeOrderToCash`, `ChangeAddress`, `Reorder`, `UnReviewedOrder` (+`UnReviewedOrderWithCurrentOrder`),
  `ValidateDeliveryTime`, `ValidateCustomerAddress`, `ValidateOrderAddressChange`, `GetUnavailableItems`
  (also `ItemReplacement`-flagged) — each a thin `IMediator.Send` wrapper; route confirmed, matching
  command handler not opened in this pass.
- `CalculateItemsReplacementTotal` (feature-flagged behind `Features.ItemReplacement`) — **now opened
  (Phase 8):** `CalculateItemsReplacementTotalCommand.cs` (~1,000 lines) recalculates an order's total
  after a customer swaps out items the restaurant marked unavailable, reusing the same
  `Order.UpdateByCustomer`/`Order.Update` recalculation path as checkout (tiered discount, offers,
  promo code, service fees all re-run per restaurant). Two confirmed bugs:
  **(1)** `ValidateOptionsConstraints` (`:897-956`) loops every option in a menu-item-price's option
  category and unconditionally does `toBeAddedCartItem.CartItemOptions.FirstOrDefault(...).Quantity`
  (`:933-936`) — if the customer didn't select a given option in that category (normal when a
  category allows fewer selections than it lists), the `FirstOrDefault` returns null and this throws
  `NullReferenceException` instead of skipping that option.
  **(2)** `RemoveRestaurantFromOrder` (`:595-644`) reads `customerAddress.AreaId` (`:669`) where
  `customerAddress` was only assigned `if (order.UserAddressId.HasValue)` (`:660-665`) — an order with
  no `UserAddressId` throws `NullReferenceException` here.
- `GetUnavailableItems`'s `ItemReplacement`-flagged sibling action — **now opened (Phase 8):**
  `NotifyCustomerToReplaceItemsCommand.cs` (~800 lines) is what the restaurant portal calls when a
  merchant marks order items unavailable/replaceable during the pending window. Three confirmed bugs:
  **(1)** `customerData` (`_context.Customer...FirstOrDefaultAsync()`, `:166-176`) is dereferenced
  with no null-check — if `order.CustomerId` doesn't resolve to a `Customer` row, this throws.
  **(2)** `restaurant` is looked up via `FirstOrDefaultAsync` and dereferenced unguarded in two
  separate private methods — `RejectOrderForRestaurant` (`:383-393`) and
  `RemoveUnavailableItemsAndContinue` (`:643-650`) — same unguarded-null shape as (1), just against
  `command.RestaurantId`/`restaurantId` instead of a customer.
  **(3)** `RejectOrderForRestaurant`'s partial-reject branch (order still has other, non-rejected
  restaurants) computes `Result.Failure(saveResult.ErrorMessage)` on a failed save but never
  `return`s it (`:425-431`) — falls through to an unconditional `Result.Success()` regardless of the
  save's actual outcome. The sibling full-cancel branch just above (`:404-419`) does this correctly,
  so this reads as a copy-paste that dropped the `return` keyword.
  Its companion class `ReplacementItemCreator.cs` (creates ad-hoc replacement menu items/prices when
  the merchant offers a substitute not already on the menu) was also read in full — no bugs found,
  consistently null-checks every lookup and checks every save result.
- `ProceedFirstCustomerOrderCommand` (now opened, Phase 8) — **confirmed bug:** `var saveResult =
  await context.SaveChangesAsyncWithResult();` is captured but never checked at all before an
  unconditional `return Result.Success()` — same shape as the repo-wide ignored-save-result pattern
  (`_conflicts.md` #63/#68/#69/#71/#72), a further confirmed instance. **Source:**
  `ProceedFirstCustomerOrderCommand.cs:34-35`.
- `CancelPayment`'s sibling `RegenerateURLCommand` — **now opened (Phase 8), 2 confirmed bugs:**
  regenerates an expired PayMob session URL. **(1)** In the "existing `PayMobRegisteredOrderId`" branch,
  `orderOnlinePaymet` (`FirstOrDefault` on `OrderPayments`) and `oldPayMobTransaction` (`FirstOrDefault`
  on its `PayMobTransactions`) are both dereferenced with no null-check — an order whose PayMob session
  was registered but has no transaction row recorded yet throws. **(2)** the final
  `SaveChangesAsyncWithResult()` result is captured but never checked before unconditionally returning
  `Success = true`. **Source:** `RegenerateURLCommand.cs:126-131` (bug 1), `:187-189` (bug 2).
- **Order-rejection family, now opened (Phase 8) — a repeated gap on the admin side:**
  `RejectOrderFromAdminCommand` and `RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand`
  both look up `selectedRejectedReason` (`OrderRejectedReason` by id) and dereference
  `.RejectedReasonAR`/`.ApplyRejectionPercentage` with no null-check — an invalid `RejectedReasonId`
  throws in either. Their restaurant-portal-side siblings, `RejectRestaurantOrderOverallCommand` and
  `RejectSomeItemsResturantCommand`, do the identical lookup but correctly guard it
  (`if (reason == null) return Failure(...)`) — so this looks like a gap specific to the admin-facing
  pair, not a shared helper bug. `RejectSomeItemsResturantCommand` has its own separate gap too: its
  reject-overall branch dereferences a `restaurant` lookup (`FirstOrDefaultAsync`) with no null-check,
  same shape as `NotifyCustomerToReplaceItemsCommand`'s `restaurant` bug above.
  `RejectRestaurantOrderOverallCommand` itself, and its `RemoveUnavailableItems` helper, were read in
  full and are clean — every lookup guarded, both save results checked, exceptions logged (not
  swallowed) via a wrapping try/catch that still returns a real failure.
  **Source:** `RejectOrderFromAdminCommand.cs:106-114`,
  `RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand.cs:104-107`,
  `RejectSomeItemsResturantCommand.cs:126-137`.
- `RestaurantStartCookingCommand` (now opened, Phase 8) — **confirmed bug:** looks up the matching
  `OrderRestaurantDetails` row for `request.RestaurantId`/`request.OrderId` twice in a row
  (`.Find(...).StartCooking` then `.FirstOrDefault(...).MarkOrderAsStartCooing(...)`), neither
  null-checked — a `RestaurantId` not actually part of the order throws on the first read. **Source:**
  `RestaurantStartCookingCommand.cs:65-75`.
- `ReorderCommand` (now opened, Phase 8) — **2 confirmed bugs:** rebuilds a cart from a past delivered
  order. **(1)** `customerAddressId.Value` and `customerData.CurrentAreaId.Value` both dereference a
  nullable int's `.Value` with no `.HasValue` check — an order/address with a null
  `UserAddressId`/`CurrentAreaId` throws. **(2)** when re-adding a previously-ordered item back to the
  cart, `option` and `menuItemPrice` (both provably nullable — computed through `?.` chains just
  above) are dereferenced unguarded (`option.OptionPrice`, `menuItemPrice.Price`, and `menuItemPrice`
  passed straight into `AddItem`) — a reordered item whose price/option was since removed or
  deactivated throws, instead of being skipped the way `ValidateRestaurantItemsAvailability` already
  does for the equivalent case earlier in this same file. **Source:** `ReorderCommand.cs:98,109` (bug
  1), `:230-287` (bug 2) — contrast `:662-671` in the same file, which guards the identical lookup
  correctly.
- `SendTawkToNotificationToCustomerCommand` (now opened, Phase 8) — **confirmed bug:** its join uses
  `orders.CustomerId.Value` with no `.HasValue` check — an order with a null `CustomerId` (e.g.
  external-delivery orders, which have no real customer row) throws `InvalidOperationException`.
  **Source:** `SendTawkToNotificationToCustomerCommand.cs:43-44`.
- `UpdateOrderByOrderCodeCommand`/`UpdateOrderCommand` (now opened, Phase 8) — **confirmed bugs:**
  `UpdateOrderByOrderCodeCommand` dereferences `order` with zero null-check at all. `UpdateOrderCommand`
  explicitly defaults `customerAddress = null` and only conditionally assigns it, then unconditionally
  dereferences `customerAddress.AreaId` right after — the null path is the deliberate default, not an
  edge case; its "new detail" creation branch also has 3 more unguarded lookups (`item`, `restuarant`,
  `price`) that throw on a stale client-supplied id. **Source:** `UpdateOrderByOrderCodeCommand.cs:27-29`;
  `UpdateOrderCommand.cs:582-589` (customerAddress), `:433-469` (new-detail lookups).
- **Payment flows:** `CreateNewSession` (PayMob session start), `PayMobProcessCallBack` (`[AllowAnonymous]`
  webhook — dispatches based on `callBackType.type`, e.g. `"TOKEN"`, confirmed by reading the callback's
  opening dispatch but not its full branches), `ChangePaymentOnlineStatus` (`[AllowAnonymous]`),
  `CancelPayment`, `CallIntentionAPIForApplePay`, `RegeneratePaymentUrl/{orderId}`,
  `GetPendingOnlinePayment` — all route-confirmed, handler internals not traced.
- `CancelOrder` and the checkout-creation path (`CreateOrderFromCartCommand`) remain the only two
  routes with full handler-level citations in this note (Rules above).

This closes the **route-inventory** gap (every route is now named and mapped to its command) but not
the **handler-depth** gap — a future pass should read each command handler above for full rule
citations, matching the depth already given to `CreateOrderFromCartCommand`/`CancelOrder`.

**Update (2026-08-03): `CreateOrderFromCartCommand` is now read in full, end to end** (all ~1,160
lines — the back half was the last known specific gap from the original session). See
[[Checkout-Payment-Processing|Checkout Payment Processing]] for the
payment-strategy pattern (CIB/PayMob card/wallet/Apple Pay), the order-saved-before-payment-session
sequencing, per-item daily/per-order quantity limits, and area-coverage/online-acceptance validation.

## Open Questions
- [ ] The auto-approve gate condition (Rule 2) is duplicated near-verbatim between
  `CreateOrderFromCustomerCart` (`Order.cs:2078-2094`) and `InitializeOrderStatus`
  (`Order.cs:2410-2438`) — confirm which is actually called from the checkout path (this note found
  `CreateOrderFromCustomerCart`'s inline version is what `CreateOrderFromCartCommand` actually uses)
  and whether `InitializeOrderStatus` is dead code, an alternate entry point, or a genuine
  duplicate that could drift.
- [ ] `DeliveryIntervalController` (`TalabatkAPIs/Controllers/Deliveryintevral/DeliveryIntervalController.cs`)
  has **zero action methods** — just a constructor. Either delivery-interval selection isn't
  actually exposed via this controller (dead code / work in progress), or it's exposed elsewhere.
  Not investigated further; worth confirming with the team before assuming it's simply unfinished.
- [ ] Full delivery-man assignment, restaurant confirmation, and compensation logic in `Order.cs`
  is out of scope for this pass — a future Delivery/Restaurant Portal/Admin knowledge-graph run
  should treat `Order` as an already-partially-documented shared entity (per this skill's dedup
  rule) and extend this note, not create a second competing one.
- [ ] The `OrderStatus` enum's numbering gaps (7, 9, 15-29) weren't investigated — may indicate
  removed legacy statuses.

## Related
- Business view: [[Order.business|Order]]
- [[OrderRestaurantDetails|OrderRestaurantDetails]] — per-restaurant "Portion" + Daily Pickup Tag
- [[CustomerCart.technical|CustomerCart]] — where an Order comes from
- Business-term background: [[../../../../../Talabatk.IDS/CONTEXT|Customer Ordering CONTEXT.md]] (Order fulfilment / Daily Pickup Tag / Portion section)
