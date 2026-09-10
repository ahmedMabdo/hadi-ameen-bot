---
id: 8orders/customer-ordering/order-and-fulfilment/cancellation-and-refund-technical
note_type: technical
context: Customer Ordering
feature: Order & Fulfilment
sources:
  - path: AdminUi/Controllers/Order/OrderController.cs
    sha1: 934f4250495d
  - path: Shared/SharedWeb/Helpers/OrderHelper/CheckAndCaptureOnlinePayment.cs
    sha1: 583af6c641f4
  - path: Shared/TalabatkApplication/Commands/AddNewCompensationCommand/AddNewCompensationCommand.cs
    sha1: 004a38a778bc
  - path: Shared/TalabatkApplication/Commands/CancelOrderCommand/CancelOrderCommand.cs
    sha1: 1959b7a4f8c3
  - path: Shared/TalabatkApplication/Commands/CancelPaymentCommand/CancelPaymentCommand.cs
    sha1: 93c43e7ebf8c
  - path: Shared/TalabatkApplication/Commands/NotifyCustomerToReplaceItemsCommand/NotifyCustomerToReplaceItemsCommand.cs
    sha1: 19c95ee1fbea
  - path: Shared/TalabatkApplication/Commands/RefundOnlinePaymentCommand/RefundOnlinePaymentCommand.cs
    sha1: 51c136d3af61
  - path: Shared/TalabatkApplication/Commands/RejectRestaurantOrderOverallCommand/RejectRestaurantOrderOverallCommand.cs
    sha1: 55b5e304b7f6
  - path: Shared/TalabatkApplication/Commands/UpdateCompensationStateCommand/UpdateCompensationStateCommand.cs
    sha1: 7dc1b3655d34
  - path: Shared/TalabatkApplication/DomainEventsHandlers/CompensationEventHandlers/CompensationApprovedEventHandler.cs
    sha1: da6b7db69a1a
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderNificationsEventHandler.cs
    sha1: e8501b1db140
  - path: Shared/TalabatkApplication/Services/OnlinePaymentRefundService.cs
    sha1: 3fda660302d5
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs
    sha1: 8ca4ea189b1e
  - path: TalabatkAPIs/Controllers/Order/OrderController.cs
    sha1: 0cb6a66fdb8c
  - path: TalabatkRestaurants/Controllers/Orders/OrdersController.cs
    sha1: 1f87b4a80401
last_updated: 2026-08-23
tags: [flow, technical]
---
# Cancellation, Rejection and Refund — Technical

> Bridges rather than restates: [[Money-Path.technical|Money Path]] (ledger/GL journals
> this flow feeds, including the "Rejected Orders Penalty" / "Refunded Online Payment" journals),
> [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]] (driver ledger the
> compensation branch writes into), [[Order.technical|Order]],
> [[Order.ExternalDelivery|Order — External Delivery Extension]],
> [[OrderRestaurantDetails|OrderRestaurantDetails]], [[OrderDetails.technical|OrderDetails]],
> [[WalletTransaction|WalletTransaction]],
> [[Customer.technical|Customer]],
> [[Compensation|Compensation]],
> [[DeliverymanTransaction.technical|DeliverymanTransaction]],
> [[Merchant-Accounting-and-Order-Cost|Merchant Accounting & Order Cost]],
> [[Restaurant.technical|Restaurant]],
> [[PayMob.technical|PayMob]].

## Trigger

Eight independent entry points converge on two shared domain methods (`Order.RejectOrder` /
`Order.RejectOrderByRestaurant`, step 8):

1. Customer, pre-confirmation — `POST api/Order/CancelOrder` → `CancelOrderCommand`
   (`TalabatkAPIs/Controllers/Order/OrderController.cs:1014-1033`).
2. Customer, older payment-aware path — `PATCH api/Order/CancelPayment` → `CancelPaymentCommand`
   (`TalabatkAPIs/Controllers/Order/OrderController.cs:429-454`).
3. Restaurant rejects the whole order — `RejectRestaurantOrderOverallCommand`
   (`TalabatkRestaurants/Controllers/Orders/OrdersController.cs:889-913`).
4. Restaurant reports item(s) unavailable mid-order — `NotifyCustomerToReplaceItemsCommand`, same
   controller.
5. Admin rejects — `RejectOrder` (`AdminUi/Controllers/Order/OrderController.cs:739-744`,
   `[Permission(Permissions.Order.RejectOrder)]`) → `RejectOrderFromAdminCommand`.
6. Admin rejects a `RestaurantPending` order — `RejectOrderWithRestaurantPendingStatus`
   (`OrderController.cs:767-772`, same permission) →
   `RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand`.
7. The system, unattended — a Hangfire job delayed by
   `Configuration.AutomaticRejectOrderTimeForUnCapturedOnlinePaymentInMinutes`
   (`OrderNificationsEventHandler.cs:112-128`) fires
   `RejectOrderIfCustomerDoesNotCompletePaymentProcess` (`:313-428`) if online payment is never
   completed.
8. A driver cannot hand the order over — `ChangeStatusToDeliveredCommand` with a
   `NotDeliveredReasonId` (`:46-127`). **Not** a rejection — see step 12.

A ninth mechanism, `AddNewCompensationCommand`/`UpdateCompensationStateCommand`, pays money back
*without* cancelling (steps 13-15).

## Step-by-step

1. **`CancelOrderCommand`.** Checks `order.CustomerId == command.UserId`
   (`CancelOrderCommand.cs:75-78`), the caller's own JWT-derived id
   (`TalabatkAPIs/Controllers/Order/OrderController.cs:1021-1025`). Blocked once `StatusId >= Confirmed` unless the
   order is stuck at `RestaurantPending` (`:86-91`). Resolves refund destination (step 9), marks any
   restaurant mid-replacement `CanceledAfterAlternatives` (`:121-140`), calls `order.RejectOrder`
   (step 8, `:142-149`).
2. **`CancelPaymentCommand`.** Same status gate (`:85-93`) but **carries no customer/user id at all**
   (`CancelPaymentCommand.cs:24-27`; controller passes none, `OrderController.cs:434-442`) — see
   Failure Modes. Re-checks the gateway directly before cancelling: legacy gateway via
   `CheckAndCaptureOnlinePayment.CreateAsync` (`:100-127`,
   `Shared/SharedWeb/Helpers/OrderHelper/CheckAndCaptureOnlinePayment.cs:13-30`) or PayMob via
   `InquireTransactionByOrderDetails` (`:128-140`). If the charge already cleared, the handler
   captures it instead and refuses to cancel (`Order.WanttoCancelPayment`, `Order.cs:4280-4284`).
   Otherwise shares `CreateWalletTransactionForOrderCancellationRefund` with `RejectOrder`.
3. **`RejectRestaurantOrderOverallCommand`.** Valid only while `Pending`/`RestaurantPending` and this
   restaurant's sub-order `Pending`/`RestaurantView` (`:106-140`). Sets the restaurant's
   `OrderRestaurantDetails` to `Rejected` with
   `ShouldApplyPenality(reason.ApplyRejectionPercentage, restaurant.RestaurantRejectionPenaltytExemption)`
   (`:179-180`) — the restaurant absorbs a penalty flag unless exempted; how that flag becomes a
   deduction is the ERP "Rejected Orders Penalty Journal," not traced here (bridge Money Path). If
   this is the last/only restaurant, or all are now rejected, the **whole order** rejects via
   `IOrderRejectionService.RejectOrderAsync` (`:192-214`, step 8 variant). Otherwise, if the
   customer's `UnavailableItemsPreference` is `RemoveAndContinue`, the rejected restaurant's items are
   stripped and totals recalculated (`RemoveUnavailableItems`, `:283-446`) — can itself produce a
   partial wallet refund when the new total is lower (`:432-440`); the order is not rejected.
4. **`NotifyCustomerToReplaceItemsCommand`.** Valid only while `Pending`/`RestaurantPending`
   (`:112-124`). Branches on `UnavailableItemsPreferences` (`SuggestAlternatives=0`,
   `RemoveAndContinue=1`, `CancelOrder=2`): `CancelOrder`, or `SuggestAlternatives` with no
   alternatives actually offered (`ShouldRejectOrder`, `:333-340`), or `RemoveAndContinue` with the
   order's only restaurant fully rejected (`:184-188`) → whole-order reject via
   `RejectOrderForRestaurant` (`:342-433`); `RemoveAndContinue` otherwise → items removed, order
   continues (`RemoveUnavailableItemsAndContinue`, `:435+`, same shape as step 3); otherwise → items
   marked `HasAlternatives`/`Unavailable`/`Available` (`:232-234`), replacement options persisted to
   `OrderDetailReplacements` (`:237-261`), restaurant sub-status → `ItemsUnderReplacement`
   (`:272-276`), customer notified to choose (`:305-330`) — no money moves yet; the customer-facing
   follow-up was not traced.
5. **`RejectOrderFromAdminCommand`.** Blocked only on `Rejected`/`Delivered` (`:81-89`) — admin can
   reject an order that already has a driver assigned or is `OnWay`, wider reach than any other
   trigger. Dereferences the looked-up `OrderRejectedReason` with no null-check — **#96**,
   `RejectOrderFromAdminCommand.cs:96-104,133-136`. Calls `order.RejectOrder` (`:125-136`).
6. **`RejectOrderFromAdminWhileOrderStatusRestaurantPendingCommand`.** Re-reads the order filtered on
   `StatusId == RestaurantPending` (`:63-73`) and checks whether any restaurant has since acted
   (`:85-96`); if so, refuses to reject and returns a summary of what each restaurant did instead
   (`:164-181`). If untouched, calls `order.RejectOrder` (`:139-142`). Same unguarded lookup — **#96**,
   `:101-104,139-142`.
7. **`RejectOrderIfCustomerDoesNotCompletePaymentProcess`.** Fires only if the order is still `Pending`
   and its online `OrderPayment` is still `Pending`/`Failed` (`:333-360`). Calls `order.RejectOrder`
   with `createdBy: "System"` (`:400-407`); nothing was captured, so the refund machinery below is
   mostly a no-op.
8. **Shared core — `Order.RejectOrder` (`Order.cs:3606-3653`) / `RejectOrderByRestaurant`
   (`:3654-3731`).** No-op if already `Rejected`. Calls `ProcessRefundAndCancelPayments` (step 9)
   *before* touching status; per restaurant, applies the penalty flag and sets
   `RestaurantOrderStatus` to `Rejected` or `Canceled` (`:3591-3614`/`3672-3695`); sets
   `Order.StatusId = Rejected`, stores the reason, bumps `OrderVersion` (`:3616-3620`); cancels any
   `New` `OrderDelivery` rows (`:3622-3625`); resets voucher/promo/tiered-discount usage
   (`:3627-3638`); removes outgoing delivery cash compensations (`:3640`); writes
   `OrderStatusHistory` (`:3642`/`3721`); fires `OrderRejectedEvent`, `RoboCallOrderRejectionEvent`,
   and a logistics sales-return event for ERP (not traced further).
9. **`ProcessRefundAndCancelPayments` (`Order.cs:3738-3801`).** Guarded by
   `IsOrderRefundedAfterReject` so a second reject on the same order can't double the refund
   (`:3747`). If destination is `Bank` and there's a genuine (non-PayMob-wallet) online capture, only
   the wallet leg is refunded to wallet and the online leg is left for the bank-refund step; otherwise
   wallet+online combine into one wallet credit
   (`CreateWalletTransactionForOrderCancellationRefund`, `:3803-3855`). Uncaptured `OrderPayments`
   rows are marked `Cancelled` (`:3793`); a captured online payment stays `Captured` pending the
   bank-refund step.
10. **`OnlinePaymentRefundService.ResolveDestinationAsync` (`:98-138`).** Precedence: `Features.AutoRefund`
    off → `Wallet` (`:112-115`); partial cancel (steps 3/4) → `Wallet` (`:117-120`); PayMob-wallet
    payment → `Wallet` (`:122-125`); mixed wallet+online → `Wallet` (`:127-130`); customer-initiated
    explicit choice → honored (`:132-135`, not exercised by any of the eight triggers); otherwise the
    customer's saved `OnlinePaymentRefundPreference` (`Wallet=0`/`Bank=1`, `:137`).
11. **`ApplyBankRefundAfterRejectIfNeededAsync` → `TryRefundOnlineAmountToBankAsync`
    (`:436-459`,`140-225`).** Runs only after the reject's own save succeeded (`:443`) and only if no
    refund executed yet (`order.ExecutedRefundDestination`, `:445`). Calls PayMob's
    `ReverseTransactionAsync` (`:179-181`) **before** its own save (`:196`) — see Failure Modes. On
    success: marks payment `Refunded`, sets `ExecutedRefundDestination = Bank`, logs an action record
    (`:187-194`). On failure: falls back to a wallet credit (`CreditWalletAsFallback`, `:261-304`) but
    deliberately leaves the payment `Captured` so an admin can retry the real reversal later.
12. **`RefundOnlinePaymentCommand` → `TryConvertWalletRefundToBankAsync`
    (`RefundOnlinePaymentCommand.cs:33-51`, `OnlinePaymentRefundService.cs:306-434`).** Dispatched
    from `POST Refund` (`AdminUi/Controllers/Order/OrderController.cs:164-186`). Valid only on a `Rejected` order
    with the online amount confirmed sitting in the wallet (`IsOnlineAmountHeldInWalletAsync`,
    `:490-513`) and not already bank-refunded (`:329-344`); checks wallet balance covers the amount
    (`:358-362`); reverses at PayMob (`:372-374`, before its own save — see Failure Modes); withdraws
    the wallet credit; marks `Refunded`; sets `ExecutedRefundDestination = Bank` (`:389-413`).
13. **Driver can't deliver — `ChangeStatusToDeliveredCommand` + `NonDeliveryReason`
    (`:46-127`).** Requires `OnWay` (`:71-74`). With a `NotDeliveredReasonId` supplied,
    `Order.ChangeOrderDeliverdAtDate` (`Order.cs:3298-3333`) still sets `StatusId = Delivered` and
    additionally `IsNotDelivered = true` (`:3310-3311`) — **not** a rejection. `OrderDeliveredEvent`
    still fires (`:3325`, feeding the full merchant/driver ledger posting in Money Path step 7); only
    loyalty/first-order/shift-bonus events are skipped (`:3326-3331`). **No refund or compensation is
    triggered automatically** — see Failure Modes.
14. **`AddNewCompensationCommand` (`:62-183`).** Not a cancellation. Auto-approves only if the order's
    running `TotalCompensation` stays within `Configuration.CompensationLimit`/`CompensationPercentage`
    of `order.Total` (`:127-138`); if approved and payout is `Wallet`, credits the wallet directly
    (`:149-168`); if `Cash` and order is `Delivered`, credits the delivering driver's ledger instead
    (`AddDriverSettlementTransaction`, `:277-305`) — the driver hands cash back, offset against what
    they owe the company. Above threshold, stays `InReview` with no payout yet.
15. **`UpdateCompensationStateCommand`.** Requires `CompansationApproval` permission via a hand-rolled
    join, not the `[Permission]` attribute pattern used elsewhere (`:44-56`). Valid only while
    `InReview` (`:71-74`). On wallet-method approval, casts the order's nullable `CustomerId` to `int`
    with no `.HasValue` check — **#109**, `UpdateCompensationStateCommand.cs:96-104`.
16. **`CompensationApprovedEventHandler` (`:34-107`).** Fired after either approval path.
    `CompensationToType`: `Restaurant=1, Delivery=2, Company=3, Operator=4`. If `Delivery`, debits the
    driver's ledger and recomputes `RequiredPayment`/`ExceededCashLimit` (`:57-95`). If `Restaurant`,
    debits the restaurant's `MerchantStatementTransaction` ledger, fetched with **no null-check** —
    **#265**, `:99-104`. If `Company`/`Operator`, **no ledger entry is written by this handler** — the
    platform (or the responsible staff member, for `Operator`) absorbs the cost with no traced
    offsetting transaction.

## Data written

1. `Order.StatusId`/`RejectedReason`/`ResponseDate`/`OrderVersion`/`IsOrderRefundedAfterReject`/
   `ExecutedRefundDestination` — every reject, `Order.cs:3606-3801`.
2. `OrderRestaurantDetails.RestaurantOrderStatus`/`.ApplyPenality` — every reject,
   `Order.cs:3591-3614`/`3672-3695`, `OrderRestaurantDetails.cs:269-272`.
3. `OrderDelivery` rows for cancelled `Initialize` **and** `New` requests — `Order.cs:3269-3275`,
   now extracted into `CancelActiveOrderDeliveries()` and called from three sites
   (`Order.cs:3251`/`3654`/`3730`). The `Initialize` status was added to the filter upstream: a
   delivery request created but not yet dispatched is now cancelled too, where previously it was
   left active. Widening this filter is what the method's own comment describes as the fix for a
   cancelled order staying drawn on the delivery man's live map.
4. `WalletTransaction` (`Refund`/`OnlineRefund`) — reject-time auto-refund (`Order.cs:3803-3855`),
   bank-refund fallback (`OnlinePaymentRefundService.cs:277-287`), wallet-to-bank conversion
   (`:389-400`).
5. `OrderPayments.PaymentStatusId` — `Cancelled` (`Order.cs:3793`), `Refunded`
   (`OnlinePaymentRefundService.cs:187`/`402`).
6. `OrderStatusHistory` — every reject, `Order.cs:3642`/`3721`.
7. `OrderComment` — refund failure/fallback narration (`OnlinePaymentRefundService.cs:239`,`290`,`380-381`).
8. `TieredDiscount` usage counters decremented — `Order.cs:3638`.
9. `OrderDetailReplacements` — item-unavailable branch, `NotifyCustomerToReplaceItemsCommand.cs:243-261`.
10. `ItemReplacementReport` bookkeeping — `CancelOrderCommand.cs:135-140`, `CancelPaymentCommand.cs:187-194`.
11. `Compensation` row — `AddNewCompensationCommand.cs:84-97`, `UpdateCompensationStateCommand.cs:96-107`.
12. `WalletTransaction` (`Compensation`) — `AddNewCompensationCommand.cs:149-168`,
    `UpdateCompensationStateCommand.cs:96-107`.
13. `DeliverymanTransaction` (credit, cash compensation) — `AddNewCompensationCommand.cs:277-305`.
14. `DeliverymanTransaction`/`MerchantStatementTransaction` (debit, clawback) —
    `CompensationApprovedEventHandler.cs:57-106`.
15. `Order.IsNotDelivered`/`NotDeliveredReasonId`/`DeliveredAt`/`StatusId = Delivered` — failed
    hand-off, `Order.cs:3298-3333`.

## External calls

- **PayMob**: `AuthenticateAsync` + `InquireTransactionByOrderDetails` (pre-cancel double-check,
  `CancelPaymentCommand.cs:130-140`); `ReverseTransactionAsync` (bank refund,
  `OnlinePaymentRefundService.cs:179-181`,`372-374`). Bridge [[PayMob.technical|PayMob]].
- **Legacy card gateway** (`GateWayPaymentUrl` config, pre-PayMob orders only):
  `CheckAndCaptureOnlinePayment.CreateAsync` — direct HTTP GET, Basic auth from `MerchantId`/
  `MerchantPassword` (or `ShourtCutMerchantId`/`ShourtCutMerchantPassword`) config keys.
- **Hangfire**: delayed job for payment-timeout auto-reject (`OrderNificationsEventHandler.cs:128`);
  queued customer-notification jobs after partial-cancel/item-removal
  (`RejectRestaurantOrderOverallCommand.cs:265-266`,`442-443`,
  `NotifyCustomerToReplaceItemsCommand.cs:327-328`).
- **Push notifications** — compensation-approved notice to the customer,
  `AddNewCompensationCommand.cs:186-274`.

## Failure modes

- **#96** — unguarded rejection-reason lookup in both admin reject commands; an invalid
  `RejectedReasonId` throws instead of failing gracefully. Steps 5-6.
- **#92** — `RejectOrderForRestaurant`'s partial branch (multi-restaurant, not `CancelOrder`
  preference) computes `Result.Failure(...)` on a save failure but never returns it, falling through
  to `Result.Success()` (`NotifyCustomerToReplaceItemsCommand.cs:425-431`). Step 4.
- **#91** — three more unguarded lookups in the same command: `customerData` (`:166-176`), `restaurant`
  in `RejectOrderForRestaurant` (`:383-393`) and in `RemoveUnavailableItemsAndContinue` (`:643-650`).
  Step 4.
- **#60** — `CancelPaymentCommand` returns `Success = true` on both rejection branches — order not
  found, order already past confirmation (`:82-86`) — despite nothing being cancelled. Same
  inverted-success shape as the broader **#396** family (six other, unrelated sites); this is the
  instance living in cancellation. Step 2.
- **#109** — `UpdateCompensationStateCommand` casts nullable `Order.CustomerId` to `int` with no
  `.HasValue` check. Step 15.
- **#265** — `CompensationApprovedEventHandler.AddMerchantCompensationTransaction` loads the
  restaurant with no null-check, unlike its guarded deliveryman sibling in the same file. Step 16.
- **#340 (bridged)** — `MerchantStatementTransaction` (step 16's clawback) is cascade-deletable off
  `Restaurant`, per [[Money-Path.technical|Money Path]]'s own entry; not re-investigated
  here.
- **Irreversible external call before the authoritative save** (same shape as the #419 family, not
  one of its ten registered instances — observed here, not cross-verified). Both
  `TryRefundOnlineAmountToBankAsync` (`:179-196`) and `TryConvertWalletRefundToBankAsync` (`:372-414`)
  call PayMob's non-idempotent `ReverseTransactionAsync` *before* `SaveChangesAsyncWithResult()`. If
  that save fails after PayMob has already reversed the charge, `ExecutedRefundDestination` stays
  unset in the DB, so a retry can call PayMob's reversal a second time for the same order. Steps
  11-12.
- **No ownership check on `CancelPaymentCommand`** (observed here, not a registered
  `_idor-instances.md` entry). No customer/user id anywhere in the command or its call site
  (`CancelPaymentCommand.cs:24-27`, `OrderController.cs:434-442`) — contrast `CancelOrderCommand`,
  which checks ownership (`:75-78`). Any authenticated customer who knows another customer's
  `orderId` can cancel it and trigger that customer's refund. Step 2.
- **`Refund` admin action has no route-level `[Permission]`** (observed here, not registered).
  `AdminUi/Controllers/Order/OrderController.cs:164-169` carries only the class-level `[Authorize]` (`:82`), unlike
  the sibling `RejectOrder`/`RejectOrderWithRestaurantPendingStatus`/`GetOrderDeliveryRequests`
  actions, which all require a specific `[Permission]`. Step 12.
- **Failed hand-off has no automatic money-back path.** `ChangeStatusToDeliveredCommand` with a
  `NotDeliveryReason` marks the order `Delivered`/`IsNotDelivered` and fires the full
  `OrderDeliveredEvent` ledger posting, but never calls `OnlinePaymentRefundService` or creates a
  `Compensation`. A customer who paid online for an undelivered order gets nothing back unless a
  human separately files one (step 14). Step 13.

## Open Questions

- `RejectOrderDeliveryRequestCommand` rejects an `OrderDelivery` *request* (routing/assignment), not
  the order itself — out of this flow's scope on inspection.
- `RejectSomeItemsResturantCommand` (203 lines) looks like a second restaurant-side partial/whole
  reject entry point alongside `RejectRestaurantOrderOverallCommand` — not opened in this pass;
  live-alternate vs. superseded legacy is unconfirmed.
- `ChangeOrderToCashCommand` (converts a `Pending`, uncaptured-online-payment order to cash) was read
  only partially; its caller and relationship to step 7's auto-reject were not confirmed.
- How the `ShouldApplyPenality` flag becomes an actual restaurant deduction (the "Rejected Orders
  Penalty Journal" in Money Path's journal list) was not traced.
- Whether `NonDeliveryReason.UpdateAdminStatus`/`UpdateDriverStatus`'s cross-field rule interacts with
  this flow beyond supplying the reason text in step 13 was not traced.
- `OrderCostHolder` — no reference to it found in any command read here; appears to belong to
  driver-bonus accounting, not cancellation/refund.
- `ISend_SMS`/`ICheckAndCaptureOnlinePayment` are injected into `RejectOrderFromAdminCommand` with no
  call site found inside its `Handle` — dead parameters or an unread branch, not confirmed.
- The customer-facing confirm/choose step after `NotifyCustomerToReplaceItemsCommand` leaves an order
  at `RestaurantNotAvilableItems`/`ItemsUnderReplacement` was not traced.
- Whether a `Compensation` against `CompensationToType.Company`/`Operator` is ever reconciled through
  a ledger not visited by `CompensationApprovedEventHandler` was not confirmed.
