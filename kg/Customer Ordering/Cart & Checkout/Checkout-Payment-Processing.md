---
id: 8orders/customer-ordering/cart-and-checkout/checkout-payment-processing
note_type: single
rule_count: 10
context: Customer Ordering
feature: Cart & Checkout
sources:
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/OnlinePaymentStrategyFactory.cs
    sha1: e1939ded90ad
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/PaymentProcessingService.cs
    sha1: c2541744da09
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, transactional, technical, backend-domain]
---
# Checkout Payment Processing (closes the `CreateOrderFromCartCommand` back-half gap)

> Closes a gap flagged since the very first session: `CreateOrderFromCartCommand.cs` lines ~550-1160
> (the payment-method-specific logic after the validation gauntlet) had never been read. Now read in
> full — this note covers what was found; see
> [[Order.technical|Order.technical.md]] for the validation-gauntlet
> half already documented.

## Business Rules

### Rule 1: Persistence happens before payment-session creation, not after
- **Plain language:** The order row is saved to the database first; the online-payment session
  (PayMob/CIB/Apple Pay) is only initiated afterward, against the already-persisted order.
- **Source:** `CreateOrderFromCartCommand.cs:572-586` (cart removed, order code de-duplicated via
  `EnsureUniqueOrderCodeAsync`, daily pickup tags allocated via `EnsurePickupTagsAsync`, order saved)
  happens **before** `:617-628` (`PaymentRequest` built, `paymentProcessingService.ProcessPayment`
  called). If payment-session creation fails or times out, the order already exists in the database
  in a non-paid state — worth confirming there's a reconciliation path for this (not traced further).

### Rule 2: A domain event only fires for orders that reach `RestaurantPending` immediately
- **Source:** `:610-613` — `NewOrderAdded` is published only `if (order.StatusId ==
  (int)OrderStatus.RestaurantPending)` — an order that lands in the `Pending` gate (see
  `Order.technical.md` Rule 2) does not notify the restaurant yet; presumably a separate event fires
  once/if it's later approved out of `Pending` (not traced in this pass).

### Rule 3: Online-payment provider selection is a 4-way strategy pattern
- **Plain language:** Which payment provider actually processes an online payment depends on a
  global "is PayMob enabled" config flag first, then the specific request flags.
- **Source:** `OnlinePaymentStrategyFactory.GetPaymentStrategy` (`OnlinePaymentStrategyFactory.cs:30-50`):
  1. If PayMob is globally disabled (`config["ApplyPayMob"]`) **or** the request didn't ask for PayMob
     (`!paymentRequest.UsePayMob`) → **CIB** (a different payment gateway entirely,
     `CibPaymentStrategy`) — this takes priority over every PayMob-specific flag below.
  2. Else if `ApplePay` → `PayMobApplePaymentStrategy` — calls
     `IPayMobApplePayIntention.ApplePayCreateIntention`, returns a `clientSecret`/`publicKey` pair
     (not a redirect URL) — a different response shape from the other three strategies.
  3. Else if `PayWithPayMobWallet` → `PayMobSmartWalletPaymentStrategy` — calls
     `IPayMobProviderServices.InizializeWalletPayment`, returns a `payMobOrderId` + a redirect `url`.
  4. Else → `PayMobCreditCardPaymentStrategy` (default PayMob card flow, not opened in full in this
     pass — assumed to mirror the wallet strategy's shape based on the interface).
- **Below the minimum threshold, no session is created at all:** `PaymentProcessingService.ProcessPayment`
  (`:29-39`) returns an empty `OnlinePaymentSessionResult` (no error) if there's no online payment
  method on the order, or if the online amount is below `Configuration.MinimumOnlinePaymentAmount` —
  a silent no-op, not a failure, in both cases.

### Rule 4: Successful PayMob-family payments write back onto the `Order` itself
- **Source:** `PaymentProcessingService.cs:57-66` — a returned success indicator sets
  `order.SetPaymentIndicator(...)`; a returned `PayMobOrderId` calls
  `order.RegisterPayMobOrderId(id, payWithPayMobWallet)` — both persisted via a second `SaveChangesAsyncWithResult`
  call after the strategy runs (a second round-trip after the order's initial save in Rule 1).

### Rule 5: Per-item purchase-quantity limits are checked against a rolling "business day" window, not calendar midnight
- **Source:** `ValidatePriceQuantity` (`:700-811`) — only runs for cart items whose
  `MenuItemPrice` has both `MaximumQuantityPerDay > 0` and `MaximumQuantityPerOrder > 0` configured.
  The "day" boundary is `nowDate.StartWorkingTime(startOffset, endOffset)`/`EndWorkingTime(...)` using
  configured `StartOffset`/`EndOffset` values — not literal midnight-to-midnight — consistent with
  this codebase's general pattern of business-day (not calendar-day) boundaries for daily limits (see
  also `OrderRestaurantDetails.PickupTag`'s daily counter in the already-documented Order note). Two
  separate checks: per-order quantity (rejects immediately) and per-day quantity (sums today's
  already-delivered/non-rejected orders for the same phone number + adds this cart's quantity).

### Rule 6: Area-coverage validation names the specific non-covering restaurants
- **Source:** `ValidateRestaurantsCoverCustomerArea` (`:663-698`) — checks every cart restaurant
  against `TA_RestaurantArea` for the customer's selected area; on failure, names the specific
  restaurant(s) that don't cover it (bilingual message), rather than a generic rejection.

### Rule 7: Mart-specific quantity validation is a separate service, with its own error formatting
- **Source:** `CheckMartQuantity` (`:857-893`) delegates to `martQuantityValidationService.ValidateCartQuantitiesAsync`
  (not opened in this pass) — a distinct availability-quantity check from `ValidatePriceQuantity`
  (Rule 5), specific to Mart-category items.

### Rule 8: Tips are only saved as a reusable default if paid online and the customer opted in
- **Source:** `SaveLastTipsValue` (`:813-843`) — no-ops if `onlineAmount == 0` or `!saveTipsAmount`;
  otherwise creates or updates a `CustomerSavedTipsConfiguration` row. Cash-only orders never persist
  a saved-tip default, regardless of the `saveTipsAmount` flag.

### Rule 9: Online-payment restaurant-acceptance gate is feature-flagged and only blocks, never silently strips
- **Source:** `HandleOrderRestaurantDetailsData` (`:927-984`) — if the order has any online/wallet
  payment, the `OnlineContribution` feature is on, and **any** restaurant in the order doesn't accept
  online payment, the **entire order is rejected** (naming the non-accepting restaurants) rather than
  silently falling back to cash-only for those restaurants. Otherwise, sets each `OrderRestaurantDetails`'
  `CashOnReceived` flag and (if applicable) the online-contribution percentage per restaurant.

### Rule 10: PayMob callback and session-generation handlers ignore save failures throughout
- **⚠️ Confirmed bug pattern (grep-swept, not just single-file):** `PayMobCallBackCommand` — the
  actual webhook handler that PayMob calls to confirm payment/refund outcomes — calls
  `SaveChangesAsyncWithResult()` **six separate times** (`:138,160,232,266,315,333`, across the main
  `Handle` and the private `ProcessInitialRefundAsync`/`ProcessFullRefundAsync`/
  `CompleteDirectBankRefundAsync` helpers) and never once checks the result of any of them — a silent
  DB failure on any of these leaves `Order`/`WalletTransaction`/`OrderPayment` state inconsistent with
  what PayMob believes happened, with no error surfaced anywhere.
- Same shape in `GenerateNewPayMobCardSessionCommand` (`:110,134,192,212`, all 4 save calls in the
  method unchecked) — a save failure here would still hand the customer a working-looking PayMob
  redirect/wallet URL whose `PayMobOrderId` link never persisted server-side, which the callback above
  would then have nothing to match against.
- See `_conflicts.md` #72 for the full cross-file list (11 confirmed instances this pass alone) — this
  is a repo-wide pattern in the `SaveChangesAsyncWithResult()` convention, not isolated to payments.

## Key helper methods (thin data-fetch wrappers, each opens its own short-lived scoped DB context)
`FetchCartAsync`, `FetchConfigurationAsync`, `FetchWalletBalanceAsync` (computed as
sum-of-non-withdrawals minus sum-of-withdrawals from `WalletTransaction`, not a stored balance field),
`FetchCustomerAddressAsync`, `FetchIsFirstOrderAsync` (a customer is "first order" until they have
**any** `Delivered` order — an already-cancelled/pending history doesn't count),
`FetchHasDuplicateOrderAsync` (any non-Delivered, non-Rejected order at the same restaurant),
`FetchDeliveryZoneIdAsync`, `FetchCityServiceFeesDataAsync` (city tax min/max/percentage, with a
Mart-specific max-fee override — ties to [[City.technical|City]]'s already-documented
fields).

## Related
- [[Order.technical|Order]] — the validation-gauntlet half of this same command
- [[CustomerCart.technical|CustomerCart]]

## Open Questions
- [ ] `PayMobCreditCardPaymentStrategy` (the default PayMob path) not opened in full.
- [ ] What reconciles an order that saved successfully (Rule 1) but whose payment-session creation
  then failed.
- [ ] What fires the restaurant-notification event for an order that starts in `Pending` and is
  later approved (Rule 2) — not traced.
- [ ] `martQuantityValidationService`'s internals (Rule 7) not opened.
