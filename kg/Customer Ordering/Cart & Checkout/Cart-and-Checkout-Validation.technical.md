---
id: 8orders/customer-ordering/cart-and-checkout/cart-and-checkout-validation-technical
note_type: technical
context: Customer Ordering
feature: Cart & Checkout
sources:
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/AddNewCartItemCommand_V1.cs
    sha1: 48c497cb1c32
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/ValidateItemOptionsCommand.cs
    sha1: c72c2ed43edc
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/MakeOrderCommand/MakeOrderCommand.cs
    sha1: 8632380200e6
  - path: Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs
    sha1: f556ad73bbcf
  - path: Shared/TalabatkApplication/Queries/GetCustomerCartSummaryQuery/GetCustomerCartSummaryQuery.cs
    sha1: f6bb6edfa97a
  - path: Shared/TalabatkApplication/Queries/ValidateCustomerCartQuery/ValidateCustomerCartQuery.cs
    sha1: fa4c00cca432
  - path: Shared/TalabatkApplication/Services/MartQuantityValidationService.cs
    sha1: 085c128a5b0d
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerCart.cs
    sha1: 1fddf55bade3
  - path: TalabatkAPIs/Controllers/Cart/CartController.cs
    sha1: 400452213f9f
last_updated: 2026-08-23
tags: [flow, technical]
---
# Cart & Checkout Validation — Technical

> Bridges [[CustomerCart.technical|CustomerCart]] (entity rules — this note traces the
> *process*), [[MenuItem.technical|MenuItem]],
> [[Order.technical|Order]],
> [[Order-Lifecycle.technical|Order Lifecycle]] (post-creation — not re-traced),
> [[Discount-Resolution.technical|Discount Resolution]] (discount math — not
> re-traced), and [[Checkout-Payment-Processing|Checkout Payment Processing]] (payment-provider
> back-half of `CreateOrderFromCartCommand`, lines ~550-1160 — not re-traced). This note is the front
> half: "add to cart" through the call into `Order.CreateOrderFromCustomerCart`.

## Trigger

1. `POST Cart/AddNewCartItem_V1` (`CartController.cs:308-329`) → `AddNewCartItemCommand_V1` — the
   only add-to-cart route wired to a controller. `AddNewCartItemCommand` (no `_V1`) still exists and
   is `using`-imported (`CartController.cs:9`) but no route constructs it — dead on the live path.
2. `POST Cart/CheckOut_V1` (`CartController.cs:260-306`) → `CreateOrderFromCartCommand` →
   `Order.CreateOrderFromCustomerCart` (`Order.cs:2070+`, covered by
   [[Order.technical|Order]] — not re-traced).

Advisory, non-blocking reads: `GET Cart/TotalValidateCart` → `ValidateCustomerCartQuery`
(`CartController.cs:211-234`) and `POST Cart/ValidateItemOptions` → `ValidateItemOptionsCommand`
(`:356-379`, a dry-run a client can call before `AddNewCartItem_V1`).

## Step-by-step

### A. Add item to cart (`AddNewCartItemCommand_V1.Handle`)

1. `resolveGuestCustomerService.ResolveAsync(...)` resolves the effective `customerId`;
   `request.CustomerId == 0` marks a guest path (`AddNewCartItemCommand_V1.cs:65-93`).
2. Customer/address/area/city resolved via staged lookups, not one join, so a missing link produces a
   distinct error (`:102-157`). Guest matched by `IsDefault` address; real customer by
   `Cart.CustomerAddressId` (`:114-118`).
3. Rush-time check: `cityRushTimeCheckService.IsAreaBusyDueToRushTime` → `"RestaurantBusy"` on true
   (`:170-175`).
4. Cart fetched/created, tracked, with items+options included (`GetOrCreateCustomerCart`, `:622-641`).
5. **Multi-restaurant cap**: `IsAllowedNumberOfRestaurantsPerOrderExceeded` (`CustomerCart.cs:266-270`)
   — true when the cart already has `>= numberOfRestaurantPerOrder` distinct restaurants and the new
   item's restaurant isn't one of them → `"MaxiumRestaurantPerOrder"` (`AddNewCartItemCommand_V1.cs:180-185`).
6. `ValidateRestaurantData` (`:396-445`): restaurant must cover the area (else
   `"RestaruantNotCoverArea"`); **opt-out check** — any restaurant in the set with
   `SupportMultipleRestaurantOrder == false` plus more than one restaurant → `"NonBundlingRestaurantExistError"`
   naming it (`:408-417`); every cart item's `DeliveryZoneId` must equal the new restaurant's, else
   `"MultiDeliveryZoneError"` (`:419-423`); restaurant must be open (`:426-435`) and have no active
   busy-history row (`:437-442`).
7. If the city has `EnableMultiRestriction` on: every existing cart restaurant's location must be
   within `DistanceBetweenRestaurantsInMeter` of the new one, else `"RestaurantDistanceValidationError"`
   (`:216-227`, `:576-620`).
8. Menu item + price + options loaded in one filtered, split query (`:232-244`).
9. `ValidateSelectedMenuItem` → `ValidateOptionsConstraints` (`:448-558`): item must exist and pass
   `(!isMartItem && !MenuItem.IsAvaliable(nowDate)) || !Active || (!isMartItem && !MenuCategory.Active)
   || (isMartItem && availableStock == 0)` else `"ItemNotAvalible"` (`:465-472`) — the **strict**
   `MenuItem.IsAvaliable` (no `Available`-flag short-circuit), contrast Step D2. Price tier must exist
   and be `Available` (`:475-488`). **`#395`** — option check here is only `option.Active == false`
   (`:529-533`); it skips the parent item's `Active`/`IsAvaliable` that
   `ValidateItemOptionsCommand.ValidateOptionsConstraints` (`ValidateItemOptionsCommand.cs:220-222`)
   checks, so an option on a deactivated or out-of-window item can still be added. Per-category
   min/max and single-select checks are otherwise identical (`:538-554` vs. `ValidateItemOptionsCommand.cs:231-247`).
10. Offer validity if `OfferItemId` supplied: `offer.CheckOfferIsValid(nowDate)` else `"OfferNotValid"`
    (`:271-287`).
11. **Mart stock re-check, silent cap**: `martQuantityValidationService.GetAvailableQuantityAsync`
    (`:252-254`, local stock or ERP lookup, `MartQuantityValidationService.cs:242-303`) — if requested
    quantity exceeds `MaximumQuantityPerOrder` capped by available stock, `Quantity` is **silently
    reduced** and the response carries `AvailableQuantity` + an adjustment message (`:290-308`,
    `:377-384`), never rejected. `GetAvailableQuantityFromERPAsync` returns `null` (no restriction) on
    any ERP failure or missing barcode (`MartQuantityValidationService.cs:288-303`) — contrast the
    checkout-time mart check in Step E9, which fails closed.
12. `CustomerCart.AddItem` (`CustomerCart.cs:65-133`) runs the merge/price-change logic in
    [[CustomerCart.technical|CustomerCart]] Rules 1-2, then `CalculateCartTotal()`
    recomputes all three running totals from the full `CartItems` collection (`:187-193`) — never
    incremented.
13. Tiered discount assigned to every cart item for this restaurant (`:341-344`); on the guest path a
    client-supplied discount id is locked only if server-verified `AvailableToGuests` (`:355-365`).
    Discount math itself: see [[Discount-Resolution.technical|Discount Resolution]].
14. `context.SaveChangesAsyncWithResult()` (`:368-375`), checked; failure → `"Server Error"`.

### B. Standalone option validation (`ValidateItemOptionsCommand.cs:49-145`)

Same shape as A8-A10 but on its own endpoint (`POST Cart/ValidateItemOptions`), not wired into the
add-to-cart write path. Its `ValidateOptionsConstraints` (`:192-251`) is the **strict** three-condition
check (`:220-222`) — `#395` is exactly this command being stricter than the live add path (Step A9).

### C. Cart totals (`GetCustomerCartSummaryQuery.cs:35-73`)

`GET Cart/CartSummary` — read-only, non-blocking. Cart missing → `"Customer Cart is Empty"`
(`:37-45`). `ICalculateCustomerDeliveryFeesForCurrentAddress.CalculateCustomerDeliveryFees` returns
delivery/extra-delivery fees — **formula not traced in this pass** (no delivery-fee formula exists
anywhere else in the vault either). `IServiceFeesCalculatorService.CalculateServiceFees` — not traced.
`CustomerCartTotal`/`CartItemsSubTotal`/`TotalOfferDiscount` are read straight off the cart's own
Step A12 running totals — no independent recomputation here.

### D. Advisory cart-content validation (`ValidateCustomerCartQuery.cs:53-660`)

`GET Cart/TotalValidateCart` — **does not block checkout**; returns per-line-item problems
(`CartValidationReasonsEnum`: `RestaurantClosed=1`, `RestaurantBusy=2`, `PriceChanged=3`,
`ItemNotAvalible=4`) plus, if `totalOfItems` was supplied, a total-mismatch flag. The client uses this
to show "some items changed" banners before `CheckOut_V1`; the real gate is Step E.
1. Restaurant open/busy per distinct restaurant (`:77-133`).
2. **`#406`** — `IsAvailable = !(!x.MenuItem.Available && NotAvailableFrom.HasValue &&
   NotAvailableTo.HasValue && nowDate >= NotAvailableFrom && nowDate <= NotAvailableTo)` (`:271`): an
   item with `Available == true` short-circuits to "available" **regardless of its blackout window**
   — the lenient implementation. This is advisory-only; Step E's own quantity check does not
   re-validate availability windows either (see Open Questions), so the gap isn't independently
   caught downstream.
3. Offer validity, price-tier `Available`, and each item's `PriceChanged` flag surfaced (`:182-256`).
4. If `TotalOfItems` supplied: server-side total recomputed per restaurant (base → offer discount →
   tiered discount) and compared within `AcceptedDifferenceBetweenTotalOnlinewithWalletandOrderTotal`
   (`:329-655`) — logging only, no state written.

### E. Checkout gauntlet (`CreateOrderFromCartCommand.cs:113-651`)

1. Cart/`Configuration`/wallet balance fetched in parallel (`:121-129`). Missing cart → `"Cart Can Not
   Be Empty"` (`:131-134`); missing `Configuration` → `"Server Error"` (`:136-141`).
2. Any cart item `PriceChanged == true` → rejected with the enum value as the error string
   (`:143-146`).
3. Scheduled delivery must be `>= TimeInMinutesToValidateDelayOrder` minutes out (`:165-187`) and
   `<= EndWorkingTime(StartOffset, EndOffset)` (`:189-201`) — same business-day convention as the
   Daily Pickup Tag ([[Order-Lifecycle.technical|Order Lifecycle]]).
4. `FetchCustomerAddressAsync` (`:1076-1107`) is an **inner join**; `null` on no match, checked by the
   caller → `"InValid Address"` (`:218-219`), a **handled** failure. Contrast **`#352`**: legacy
   `MakeOrderCommand` dereferences the equivalent nullable unconditionally (`MakeOrderCommand.cs:226`)
   and crashes; this route does not share that defect.
5. Rush-time re-check on the resolved address's area → busy message (`:222-230`).
6. `ValidateRestaurantsCoverCustomerArea` (`:663-698`): every cart restaurant must have a
   `TA_RestaurantArea` row for the area, else a message naming the ones that don't (`:685-695`).
7. `ValidatePriceQuantity` (`:700-811`), parallel with a city-service-fees fetch (`:246-256`): only for
   prices with both `MaximumQuantityPerDay > 0` and `MaximumQuantityPerOrder > 0` set (`:721-724`,
   `:762-768`) — checks per-order cap (`:776-786`) then per-day cap using a business-day window and
   the customer's phone number across non-`Rejected` orders (`:789-798`); messages joined
   comma-separated (`:802-810`). Does **not** re-check availability windows/active flags from Step A9.
8. Promo vs. voucher **mutually exclusive by construction** (`:268-319`): non-empty `PromoCode` means
   `VoucherId` is never inspected. Voucher must belong to the customer, not be `IsUsed`, and (if
   merchant-scoped) match a cart restaurant, else `"Voucher is not valid"` / `"Voucher is used
   before"` / `"Voucher cannot be applied to this order."` (`:296-316`).
9. `CheckMartQuantity` (`:420-424`) → `ValidateCartQuantitiesAsync`
   (`MartQuantityValidationService.cs:46-74`) **bails with a pass result for any cart spanning more
   than one restaurant** (`:50-53`) — a multi-restaurant cart with a store item gets no checkout-time
   stock recheck at all. Single-restaurant mart carts: local mode compares against
   `CurrentStockQuantity` (`:76-136`); ERP mode fails **closed** on an ERP error or missing-barcode
   match, per its own in-code comments (`:168-180`, `:189-204`). *Cross-reference*: `_conflicts.md`
   **#263** describes this same code as failing **open** as last recorded — the code read here behaves
   oppositely at both cited spots; not overturning #263, flagged as an unconfirmed discrepancy.
10. `Order.CreateOrderFromCustomerCart(...)` (`:427-470`) builds payment split, delivery fees,
    discounts, first-order/duplicate flags, and the `isShourtCut`-gated pending/auto-approve status —
    fully covered by [[Order.technical|Order]] and
    [[Order-Lifecycle.technical|Order Lifecycle]], not re-traced. Failure →
    localized message keyed by `error.Split('|')[0]` (`:495-503`).
11. **Post-construction voucher re-check**, on the built order's actual subtotal — merchant-scoped
    compares restaurant subtotal minus tiered discount to `MinOrderAmountAtIssue`/config fallback;
    otherwise `order.Total + order.voucherValue` — failing returns a minimum-amount message
    (`:507-530`), **after** the order was already fully built.
12. **Post-construction promo-code re-check**: `promoCode.MinimumAmount` vs. summed
    `OrderRestaurantDetails.PricewithOptionAndQuantity` (`:532-545`) — same build-then-reject shape.
13. `HandleOrderRestaurantDetailsData(order)` (`:548-552`, internals not opened) — online-payment
    contribution split; failure still returned before anything persists.
14. **First DB write, cart cleared**: `context.CustomerCart.Remove(customerCart)` (`:572`) →
    `EnsureUniqueOrderCodeAsync` → `EnsurePickupTagsAsync` → `Order.AddAsync` →
    `SaveChangesAsyncWithResult()` (`:572-586`), checked; failure → `"Server Error"`. **Resolves an
    Open Question in [[CustomerCart.technical|CustomerCart]]** ("where the cart is
    cleared after checkout") — here, same unit of work as the order insert.
15. Recommendation logging, `NewOrderAdded` publish if `StatusId == RestaurantPending` (`:588-613`),
    stored-procedure refresh (`:615`) — all [[Order-Lifecycle.technical|Order
    Lifecycle]], not re-traced.
16. Payment-session creation (`:617-628`) → `paymentProcessingService.ProcessPayment` — provider
    selection fully documented in [[Checkout-Payment-Processing|Checkout Payment Processing]]. Any
    unhandled exception in the whole handler is caught (`:639-649`) and returned with raw
    `ex.Message` text — observed, not scored as a numbered finding here.

## Data written

1. `CustomerCart`/`CartItem`/`CartItemsOptions` — mutated on every `AddNewCartItem_V1` call (Step A),
   deleted at checkout (`CreateOrderFromCartCommand.cs:572`).
2. `Order`, `OrderDetails`, `OrderRestaurantDetails`, `OrderPayments` — inserted together (`:579-586`).
3. `Voucher.IsUsed` / promo-code usage counters — set inside `Order.CreateOrderFromCustomerCart`, see
   [[Discount-Resolution.technical|Discount Resolution]].
4. `CustomerSavedTipsConfiguration` — only if `SaveTipValue` and `onlinePaymentAmount != 0`
   (`:813-843`).
5. `Customer.CustomerDeliveryInstructions` — cleared/re-added only if
   `SaveSelectedDeliveryInstructionIds` (`:567-570`, `:844-855`).
6. `Order.PaymentIndicator`/`PayMobOrderId` — written by `PaymentProcessingService` after
   `ProcessPayment`, a second `SaveChangesAsyncWithResult()` (see
   [[Checkout-Payment-Processing|Checkout Payment Processing]] Rule 4, not re-traced).

## External calls

- `IResolveGuestCustomerService.ResolveAsync` — guest bootstrap (Step A1, internals not opened).
- `ICityRushTimeCheckService.IsAreaBusyDueToRushTime` — called independently at add-to-cart (A3) and
  checkout (E5) against whatever address is current at each moment.
- `IMartQuantityValidationService` → `ILogisticService.GetItemQuanaityAsync` — ERP stock, both at
  add-time (A11, permissive on error) and checkout (E9, closed on error per code read here).
- `ICalculateCustomerDeliveryFeesForCurrentAddress` / `IServiceFeesCalculatorService` — Step C and E
  (`:328`); formulas not traced.
- `IPaymentProcessingService.ProcessPayment` → PayMob/CIB — see [[Checkout-Payment-Processing]].
- `IDailyPickupTagAllocator.AllocateAsync` — Step E14, owned by
  [[Order-Lifecycle.technical|Order Lifecycle]].

## Failure modes

| Step | Trigger | Customer sees | Finding |
|------|---------|----------------|---------|
| A5 | Cart at the per-city restaurant cap, new item is a new restaurant | `"MaxiumRestaurantPerOrder <n>"` | — |
| A6 | Non-bundling restaurant mixed in / delivery-zone mismatch / closed / busy | Named error per cause | — |
| A7 | Restaurants too far apart (city restriction on) | `"RestaurantDistanceValidationError <n> Meter"` | — |
| A9 | Item inactive/out of window/category inactive (mart: zero stock) | `"ItemNotAvalible"` | Uses strict `IsAvaliable`, not #406's path |
| A9 | Option on a deactivated/unavailable parent item, via live add path | Silently **accepted** | **#395** |
| D2 | Item flagged in advisory validation | Advisory `ItemNotAvalible` entry | **#406** — lenient; doesn't block checkout either way |
| E2 | Any cart item still `PriceChanged` | Numeric `PriceChanged` code | — |
| E3 | Scheduled delivery too soon / outside business hours | Localized lead-time/hours message | — |
| E4 | No matching address for the given id | `"InValid Address"` (handled) | Contrast **#352** — legacy `MakeOrderCommand` NREs on this same case |
| E6 | A cart restaurant doesn't cover the resolved area | Message naming the restaurant(s) | — |
| E7 | Per-order/per-day purchase cap exceeded | Formatted max-quantity message | Does not re-check availability windows |
| E8 | Voucher invalid/used/merchant-mismatched | Voucher-specific message | — |
| E9 | Mart stock insufficient (single-restaurant only) / ERP unreachable | Stock message / "can't verify" | Multi-restaurant carts get **no** recheck; cross-ref #263 discrepancy |
| E10 | Order construction fails (payment split, discounts, etc.) | Localized message by error prefix | Internals: [[Order.technical\|Order]] |
| E11/E12 | Voucher/promo minimum unmet against the *built* order total | Minimum-amount message | Runs after full construction, not before |
| E16 | Unhandled exception anywhere in the handler | Generic message + raw `ex.Message` | Observed, not a numbered finding |
| Payment-method list (outside the E gauntlet) | Phone number has `IsStillBlocked` row in `BlockedUsersFromCOD` | Cash hidden from `GetAllPaymentsByAddressQuery` list (`:45-52`) | Not confirmed whether E independently rejects `CashAmount > 0` from the same blocked number — see Open Questions |
| #449 (context) | Shortcut-app large order via legacy `MakeOrderCommand` instead of `CheckOut_V1` | Held pending instead of auto-approved | `isShourtCut` hardcoded `false` there; `CheckOut_V1` (this note's route) honors the real flag |

## Open Questions

- [ ] Whether `BlockedUsersFromCOD` is re-checked inside `CreateOrderFromCartCommand`/
  `Order.CreateOrderFromCustomerCart` for a direct `CashAmount > 0` submission — not found in either
  file; only the list-filtering read (`GetAllPaymentsByAddressQuery.cs:45-52`) was located.
  [[BlockedUsersFromCOD]]'s own notes independently flag this as untraced.
- [ ] Delivery-fee and service-fee formulas — not opened in this pass (out of scope for a
  validation-focused note); no delivery-fee formula exists anywhere else in the vault either.
- [ ] `_conflicts.md` **#263** describes `MartQuantityValidationService.cs` as failing open on ERP
  errors; the code read for this note fails closed at the same cited lines (Step E9) — possibly fixed
  since #263 was logged, not confirmed either way, flagged for reconciliation rather than asserted.
- [ ] Whether an item's availability *window* (vs. quantity) is re-validated anywhere on `CheckOut_V1`
  — Step A9 checks it at add-time, Step E7 checks quantity only, Step D is advisory and lenient
  (#406). Not traced whether `Order.CreateOrderFromCustomerCart` internals (Step E10) re-check it.
- [ ] `HandleOrderRestaurantDetailsData` (`CreateOrderFromCartCommand.cs:548`) internals — not opened.
- [ ] Whether a failed payment-session creation leaves an orphaned, persisted, unpaid `Order` with a
  reconciliation path — already an open question in [[Checkout-Payment-Processing]], not re-investigated.
- [ ] `EditCartItemCommand`/`ChangeCartItemQuantityCommand`/`DeleteCartItemCommand`
  (`CartController.cs:331-433`) were not traced step-by-step; their entity-level behavior is already
  in [[CustomerCart.technical|CustomerCart]] Rules 3 and 4a, not re-derived here.
