---
id: 8orders/customer-ordering/cart-and-checkout/customercart-technical
note_type: technical
context: Customer Ordering
feature: Cart & Checkout
entity: CustomerCart
entity_type: legacy-poco-root
rule_count: 40
sources:
  - path: Shared/TalabatkApplication/Commands/ChangeCartItemQuantityCommand/ChangeCartItemQuantityCommand.cs
    sha1: 872b006b0f20
  - path: Shared/TalabatkApplication/Commands/ChangeCustomerCartAddressCommand/ChangeCustomerCartAddressCommand.cs
    sha1: d5809b9874a0
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkData/Mapping/CustomerCartMaping.cs
    sha1: 3b461ef795ef
  - path: Shared/TalabatkLogic/TalabatkModels/CartItem.cs
    sha1: 7048d48ce442
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerCart.cs
    sha1: 1fddf55bade3
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, transactional, technical, backend-domain]
---
# CustomerCart — Technical

> **Layer:** Domain — Legacy POCO (inherits a common `entity` base with domain-event support — see Open Questions)   **Context:** Customer Ordering   **Feature:** Cart & Checkout
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/CustomerCart.cs`   **Last Updated:** 2026-08-02

The customer's active shopping cart. One per customer (by convention, not by DB constraint — see
Conflicts). Owns `CartItem` rows, tracks running totals, and carries a locked
[[TieredDiscount.technical|TieredDiscount]] across the guest→real
login transition.

## Business Rules

### Rule 1: Adding an item merges into an existing identical line
- **Plain language:** Adding the "same" item again (same menu item, same price tier, same notes,
  same set of selected options at the same quantities) increases its quantity instead of creating a
  duplicate cart line.
- **Source:** `CustomerCart.cs:78-101` (`AddItem`) — the match is on `MenuItemId` + `PriceId` +
  `CartItemNotes` + an exact set-equality check on `CartItemsOptions` (same option ids **and** same
  per-option quantities).

### Rule 2: Price-change detection on add
- **Plain language:** If an existing cart line's options are re-added at a different price than
  what's currently configured for that option, the line is flagged as price-changed and a
  domain event is raised.
- **Source:** `CustomerCart.cs:93-101, 121-130` — compares each existing `MenuItemOption.OptionPrice`
  against the incoming `CartItemOptionPoco.Price`; on a mismatch, calls
  `cartItem.MarkCartItemAsPriceChangingWithOption` and raises
  `NotifyCustomerForPriceChangingWhenAddingToCartEvent` (a genuine domain event — see Open Questions,
  this contradicts the general repo pattern of legacy POCOs not raising events).

### Rule 3: Editing an item is remove-then-add
- **Source:** `CustomerCart.cs:135-155` (`EditItem`) — removes the existing line, then calls
  `AddItem` fresh, which means Rule 1's merge logic can silently fold an edited item into another
  existing line if the edit happens to make them identical.

### Rule 4: Running totals are always recalculated, never trusted incrementally
- **Plain language:** Every mutation (add/edit/change quantity/remove/price update) ends by
  recomputing `TotalAfterDiscount`, `TotalOfferDiscount`, and `TotalBeforeDiscount` from scratch off
  the current `CartItems` collection — nothing increments these fields directly.
- **Source:** `CustomerCart.cs:187-193` (`CalculateCartTotal`), called from `AddItem`,
  `ChangeCartItemQuantity`, `RemoveCartItem`, `UpdateCartItemPrcies`.

### Rule 3a: `ChangeCustomerCartAddressCommand` is entirely commented out — the whole feature is a no-op
- **🔴 Confirmed high-severity gap:** the entire handler body (area-support validation, per-restaurant
  delivery-fee recalculation, `customerCart.ChangeCartAddress(...)`, the save) is commented out. The
  method unconditionally executes `return Result.Success();` and nothing else. Any caller of this
  command believes the cart's address was changed (and gets a success response) but **no state
  changes at all** — the cart keeps whatever address/delivery-fee data it had before. This is a
  complete feature stub, not a partial bug — same "confirmed dead gate reporting success" shape as
  `_conflicts.md` #11 (`UserPreferencesController`), but here the whole handler is dead, not just a
  feature flag.
- **Source:** `ChangeCustomerCartAddressCommand.cs:33-144` (commented out), `:145` (`return
  Result.Success()`).

### Rule 4a: Application layer — `ChangeCartItemQuantityCommand`'s max-quantity guard is dead code
- **⚠️ Confirmed gap:** the handler fetches `menuItemPrice` and the customer's `mobileNumber`
  (`:78-86`) — exactly the inputs its own private `ValidateMenuItemPriceQuantity` method needs to
  enforce `MaximumQuantityPerOrder`/`MaximumQuantityPerDay` — but never actually calls that method
  from `Handle`. The per-order/per-day quantity cap that `CalculateItemsReplacementTotalCommand`'s
  `ValidatePriceQuantity` enforces elsewhere is silently skipped when a customer changes an existing
  cart line's quantity directly.
- **Source:** `ChangeCartItemQuantityCommand.cs:50-108` (`Handle`, no call to `:110-138`
  `ValidateMenuItemPriceQuantity`).

### Rule 5: Multi-restaurant cap (checked by the caller, not enforced inside `CustomerCart`)
- **Plain language:** There's a configurable cap on how many distinct restaurants one cart can span;
  `CustomerCart` only answers "would adding restaurant X exceed the cap", it does not enforce it —
  the calling command decides what to do with the answer.
- **Source:** `CustomerCart.cs:266-270` (`IsAllowedNumberOfRestaurantsPerOrderExceeded`). This is
  consistent with `CONTEXT.md`'s note that **multi-store cart is an existing, fully-supported
  feature** (`GetMultiStoreCartQuery`) — the cap is a configured ceiling, not a single-restaurant
  restriction.

### Rule 6: Guest cart merge is "guest-replaces", not "merge and combine"
- **Plain language:** When a guest logs into an existing real account, the guest's cart entirely
  **replaces** whatever cart the real account already had — the real account's prior cart items and
  locked discount are discarded, not combined with the guest's.
- **Trigger:** Login/OTP success for a phone number that resolves to an existing Customer while a
  guest cart exists.
- **Source:** `MergeGuestCartIntoCustomerCommand.cs:148-162` — explicit, deliberate policy, stated in
  the file's own header comment. If the real account had no cart yet, a fresh one is initialized
  from the **real customer's** name/phone (not the guest's placeholder identity) —
  `MergeGuestCartIntoCustomerCommand.cs:120-147`.

### Rule 7: Guest cart merge skips restaurant/menu-item revalidation
- **Plain language:** Re-homing a guest's cart items onto the real account does **not** re-run the
  full add-to-cart validation gauntlet (restaurant open hours, busy state, multi-restaurant distance,
  rush-time, stock, offer validity) — those items already passed those checks once as the guest.
- **Why:** Explicitly documented in code as a deliberate choice: re-validating at merge time would
  let an unrelated transient condition (e.g. the restaurant happening to be closed at the exact
  moment of login) fail an otherwise-unrelated login step. The full gauntlet still runs for real at
  checkout (`CreateOrderFromCartCommand`, see below).
- **Source:** `MergeGuestCartIntoCustomerCommand.cs:166-179`.

### Rule 8: Guest's locked discount and delivery address both carry over; real account's own default address is overwritten
- **Plain language:** Along with the cart, a guest's locked Tiered Discount (Rule 6 in
  `TieredDiscount.technical.md`) and default delivery address follow them into the real account —
  and the guest's address becomes the real account's new default, replacing whatever was there.
- **Source:** `MergeGuestCartIntoCustomerCommand.cs:283-329` (discount + address carryover),
  `:401-444` (the customer's "unavailable items" preference is *also* carried over, but only if the
  guest actually changed it from the default — copying unconditionally would silently reset a
  returning customer's own preference on every guest login).

### Rule 9: Checkout validation gauntlet (`CartController.CheckOut_V1` → `CreateOrderFromCartCommand`)
Before an `Order` is created from the cart, all of the following are checked, in this order (each a
distinct rejection):
1. Cart must not be null/empty (`CreateOrderFromCartCommand.cs:135-138`). Until recently this guard
   tested `customerCart is null` only, so a cart row whose last item had been removed passed it and
   an order was created with no lines; `master` now also rejects a null or empty `CartItems`, which
   is what makes the "or empty" half of this rule true rather than intended.
2. System configuration row must exist (`:140-145` — a missing config row is a **server error**, not
   a user-facing validation failure).
3. No cart item may currently be `PriceChanged` (`:143-146`) — the customer must acknowledge/refresh
   price changes before checkout can proceed.
4. If a scheduled delivery time is requested, it must be at least a configured minimum lead time
   from now (`:179-187`, `TimeInMinutesToValidateDelayOrder`) and within the working-hours window
   (`:189-201`, `StartOffset`/`EndOffset` config, same `StartWorkingTime`/`EndWorkingTime` convention
   `TalabatkAPIs/CONTEXT.md` documents for the Daily Pickup Tag's business-day boundary).
5. The selected delivery address must resolve (`:218-219`).
6. The delivery area must not be marked busy due to rush time (`:222-230`).
7. Every restaurant in the cart must cover the customer's delivery area (`:232-241`).
8. Price/quantity re-validation against current menu data (`:249-261`).
9. **PromoCode and Voucher are mutually exclusive by construction** — if `request.PromoCode` is
   non-empty, `request.VoucherId` is never even looked at; a voucher is only considered when no
   promo code string was supplied (`:268-318`). A voucher must exist, belong to the requesting
   customer, not already be used, and (if merchant-scoped) match a restaurant actually in the cart.
10. Mart-specific stock/quantity check for cart items belonging to a store-type restaurant
    (`:420-424`, `CheckMartQuantity`).
11. `Order.CreateOrderFromCustomerCart(...)` builds the actual `Order` — this is where per-restaurant
    pricing, tiered-discount application, and payment-split validation happen; see the **Order &
    Fulfilment** feature (not yet documented) for that aggregate's own rules.
12. Post-creation, if a voucher was used, its minimum-order-amount is re-checked against the
    *resulting* order/merchant subtotal (`:507-529`) — this is a second, later voucher check distinct
    from #9's existence/ownership/usage check.
13. If a promo code was used, its `MinimumAmount` is checked against the resulting restaurant
    subtotal (`:537-545`) — mirrors #12's shape for the promo code path.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `CustomerCartId` | PK | identity |
| `CustomerId` | Owning customer (guest or real) | required — see Conflicts for the missing uniqueness constraint |
| `TotalAfterDiscount` / `TotalOfferDiscount` / `TotalBeforeDiscount` | Running cart totals | always derived, never set directly (Rule 4) |
| `CustomerName` / `CustomerMobileNumber` | Denormalized snapshot of the owning customer at cart-init time | set once in `InizaializeCart`, not kept in sync afterward (Open Question) |
| `LockedTieredDiscountId` | The Tiered Discount locked to this cart (Guest Mode retention) | nullable FK, no DB-level FK constraint found in `CustomerCartMaping.cs` (see Conflicts) |
| `CartItems` | Owned collection | cascade-deleted with the cart |

## Status / State
No status field — a `CustomerCart` simply exists (has 0+ items) or is cleared (`ClearCustomerCart`,
called both by the customer explicitly and internally by the guest-merge "discard real cart" step).
There is no "checked out" flag on the cart itself — checkout consumes the cart's current contents to
build an `Order`, then the caller is responsible for clearing it (not shown in the excerpt read for
this note; flagged as an Open Question).

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `CartItem` | Backend-Domain (legacy POCO) | Owned collection, FK `CustomerCartId` | Cascade delete. |
| `Restaurant`, `MenuItem`, `MenuItemPrice`, `OfferItem` | Backend-Domain (legacy POCO) | Read at add-time to build a `CartItem` snapshot (`CartItem.Instance`) | Cart items **copy** restaurant/menu data at add-time (name, logo, tax, profit%) rather than referencing it live — see Conflicts for the staleness implication. |
| [[TieredDiscount.technical\|TieredDiscount]] | Backend-Domain (aggregate root) | `LockedTieredDiscountId` (cart-level lock) + `CartItem.TieredDiscountId` (per-item selection) | Two distinct discount-tracking fields at two different levels — see Open Questions. |
| `PromoCodes` / `Vouchers` | Backend-Domain (legacy POCO) | Read at checkout only, not stored on the cart itself | Mutually exclusive at checkout (Rule 9.9). Full entities documented in the Discounts & Coupons feature (not yet built). |
| `Customer` (guest + real rows) | Backend-Domain (legacy POCO) | `MergeGuestCartIntoCustomerCommand` | Guest-replaces merge (Rule 6-8). |
| `CustomerAddresses` | Backend-Domain (legacy POCO) | Re-homed during guest merge | Default-address invariant explicitly preserved (Rule 8). |
| `Order` | Backend-Domain (legacy POCO) | `Order.CreateOrderFromCustomerCart(...)` | Checkout's terminal step; full rules documented under Order & Fulfilment (not yet built). |

> ⚠️ **CONFLICT/GAP — No DB uniqueness constraint on one-cart-per-customer**
> `CustomerCartMaping.cs:14-22` only sets `HasKey(x => x.CustomerCartId)` — there is **no**
> `HasIndex(x => x.CustomerId).IsUnique()`. Every read path in the codebase
> (`GetCustomerCartQuery`, `MergeGuestCartIntoCustomerCommand`, `CreateOrderFromCartCommand`'s
> `FetchCartAsync`) assumes exactly one cart per customer and uses `FirstOrDefaultAsync(c =>
> c.CustomerId == ...)`. If a race condition (e.g. two concurrent `AddNewCartItemCommand_V1` calls
> for a brand-new customer, each finding no cart and creating one) ever produced two `CustomerCart`
> rows for the same customer, every query would silently pick one and ignore the other's items —
> the database has nothing stopping this from happening.

> ⚠️ **CONFLICT/GAP — Cart items snapshot restaurant/menu data instead of referencing it live**
> `CartItem.Instance` (`CartItem.cs:147-279`) copies the restaurant name, logo, menu item name,
> image, tax rate, and profit percentage onto the cart item **at add-time**. If the restaurant
> renames itself, changes its tax rate, or the menu item's description changes while the item sits
> in a customer's cart, the cart shows stale data until the item is re-added or its price changes
> (which re-triggers `UpdateCartItemPrice`, but that only refreshes `ItemPrice`/`PriceChanged`, not
> the descriptive fields). This may be an intentional "price integrity snapshot" pattern rather than
> a bug — flagged for confirmation, not asserted as wrong.

## Rule / Decision Matrix
| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|-----------------|---------------------|---------|--------|
| 1 | Add item | Existing line matches menu item + price + notes + options exactly | Quantity merged into existing line | `CustomerCart.cs:78-101` |
| 2 | Add item | Existing option's configured price differs from what's being re-added | Line marked `PriceChanged`, event raised | `CustomerCart.cs:93-101` |
| 3 | Guest login merge | Real account already has a cart | Real cart's items + locked discount discarded, guest's take over | `MergeGuestCartIntoCustomerCommand.cs:148-162` |
| 4 | Guest login merge | Guest cart empty/missing | No-op merge; guest row is **not** deleted here (left for the 24h purge job) | `MergeGuestCartIntoCustomerCommand.cs:78-102` |
| 5 | Checkout | Any cart item `PriceChanged=true` | Rejected — must refresh prices first | `CreateOrderFromCartCommand.cs:147-150` |
| 6 | Checkout | Scheduled delivery time < minimum lead time or outside working hours | Rejected | `CreateOrderFromCartCommand.cs:179-201` |
| 7 | Checkout | `request.PromoCode` non-empty | `VoucherId` ignored entirely, even if also supplied | `CreateOrderFromCartCommand.cs:272-289` |
| 8 | Checkout | Voucher already used, or merchant-scoped voucher doesn't match a cart restaurant | Rejected | `CreateOrderFromCartCommand.cs:305-316` |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 5+ | `CartItem`, `Order` (via checkout), `TieredDiscount` (lock), `PromoCodes`/`Vouchers` (checkout-time read), `Customer`/`CustomerAddresses` (guest merge) |
| Sides touched | 3/5 | Backend-Domain, Backend-Application, Backend-Data — no dedicated Frontend form (mobile-app-only, not in this repo) or Legacy involvement found |
| Cross-context integrations | 0 direct | Cart itself doesn't cross contexts; checkout's downstream `Order` does (see Order & Fulfilment, not yet documented) |
| Domain events involved | 1 | `NotifyCustomerForPriceChangingWhenAddingToCartEvent` |
| Hub? | yes | Referenced by nearly every other Customer Ordering feature (Discounts, Order, Guest Mode) |

## Open Questions
- [ ] `CustomerCart` extends a shared `entity` base class with `AddEvent`/`Events` support
  (`CustomerCartMaping.cs:19` explicitly does `builder.Ignore(x => x.Events)`), meaning **domain
  events aren't exclusive to the 4 `*Aggregate/` folders** as `references/repo-map.md` implies —
  worth revising that guidance once more legacy POCOs are surveyed for the same pattern.
- [ ] `CustomerName`/`CustomerMobileNumber` are set once at cart initialization and not shown to be
  refreshed if the customer later changes their name/phone — confirm whether this denormalization is
  intentional (e.g. for point-in-time display) or a staleness risk.
- [ ] Two separate discount-tracking fields exist at two levels — `CustomerCart.LockedTieredDiscountId`
  (cart-wide, Guest Mode retention) and `CartItem.TieredDiscountId` (per-line, set via
  `SetTieredDiscount`). Confirm the exact relationship/precedence between the two at checkout time —
  this note infers from `GetCustomerTieredDiscountQuery` and `CreateOrderFromCartCommand.cs:397-404`
  that `CartItem.TieredDiscountId` is what actually drives per-restaurant discount application at
  order-creation, while `LockedTieredDiscountId` is closer to a UI/retention concern — not fully
  confirmed against `Order.CreateOrderFromCustomerCart`'s internals (out of scope for this note; see
  Order & Fulfilment).
- [ ] Where the cart is actually cleared after a successful checkout was not found in the code read
  for this note — confirm this happens (likely inside `Order.CreateOrderFromCustomerCart` or a
  follow-up step in the handler past the excerpt read here).
- [ ] Full `CreateOrderFromCartCommand.cs` is 1160 lines; this note covers its pre-`Order`-creation
  validation gauntlet from a targeted read, not a line-by-line audit. Payment-method-specific logic
  (PayMob, Apple Pay, wallet contribution math) was not documented here.

## Related
- Business view: [[CustomerCart.business|CustomerCart]]
- [[CartItem|CartItem]] — the owned line items and their own pricing/profit/tax rules
- [[TieredDiscount.technical|TieredDiscount]] — cart-level lock and per-item selection
- Business-term background: [[../../../../../Talabatk.IDS/CONTEXT|Customer Ordering CONTEXT.md]] (Cart, Guest mode sections)
