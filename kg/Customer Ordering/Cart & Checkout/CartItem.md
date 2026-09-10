---
id: 8orders/customer-ordering/cart-and-checkout/cartitem
note_type: single
rule_count: 10
context: Customer Ordering
feature: Cart & Checkout
entity: CartItem
entity_type: child
covers: [CartItemOptions]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/CartItem.cs
    sha1: 7048d48ce442
  - path: Shared/TalabatkLogic/TalabatkModels/CartItemOptions.cs
    sha1: 0ef4d7a3fc49
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, child, technical, backend-domain]
---
# CartItem (+ CartItemOptions)

One line in a [[CustomerCart.technical|CustomerCart]] — a specific menu item, price
tier, and set of selected options, at a quantity. `Shared/TalabatkLogic/TalabatkModels/CartItem.cs`.

## What makes this entity dense
Unlike most child entities in this codebase, `CartItem` carries real computed business logic, not
just FK pointers:

- **Snapshotted descriptive data.** Restaurant name/logo, menu item name/image, and price-tier name
  are copied in at add-time (`CartItem.Instance`, `CartItem.cs:147-279`) from the live
  `Restaurant`/`MenuItem`/`MenuItemPrice` graph — see the parent note's flagged conflict about this
  going stale.
- **Per-item discount math.** `Discount` (a computed property, `CartItem.cs:91-97`) applies
  `OfferDiscount` either as a percentage or a fixed amount depending on `IsOfferPercentage`, rounded
  to 2 decimals. `ItemPriceAfterDiscount` and `TotalItemBeforeDiscount` build on top of it.
- **Tax computation.** `SetTax` (`CartItem.cs:302-314`) backs out the tax portion of the
  discounted price using `RestaurantTaxValue` as a VAT-style inclusive rate:
  `tax = priceAfterDiscount − priceAfterDiscount / (1 + rate/100)`.
- **Profit computation.** `ApplyProfitValue` (`CartItem.cs:329-336`) computes `ProfitValue` from
  `ProfitPercentage` — sourced from either the menu **category's** profit or the **restaurant's**
  own profit, depending on `Restaurant.UseMenuCategoryProfit` (decided once, at add-time, via
  `ApplyProfitDate <= nowDate`, `CartItem.cs:263-273`). This is business-internal margin data
  carried on a customer-facing cart row, not shown to the customer.
- **Price-change tracking.** `PriceChanged` (bool) plus a per-option mirror on
  `CartItemOptions.PriceChanged` — set by the parent cart's `AddItem` (see
  `CustomerCart.technical.md` Rule 2) and cleared by `UpdateCartItemPrice` (`CartItem.cs:121-145`),
  which re-pulls the current price and re-runs the tax/profit calculation.
- **Per-item Tiered Discount selection**, distinct from the cart-level lock — see
  `SetTieredDiscount`/`RemoveTieredDiscount` (`CartItem.cs:338-346`) and the Open Question in the
  parent note about how the two interact.

## Key Fields
| Field | Meaning |
|-------|---------|
| `Quantity` | A `double`, not an integer — allows fractional quantities (e.g. weighted mart items) |
| `ItemPrice` | The price captured at add-time (`oldPrice` parameter to `Instance`) |
| `ItemPriceWithOptions` | `ItemPrice` + sum of selected options' price × their own quantities |
| `TotalOfferDiscount` / `TotalCartItem` | Computed per-line totals feeding the cart's own running totals |
| `TieredDiscountId` | Per-item Tiered Discount selection (nullable) |
| `OfferId` / `OfferItemId` | Item-level offer applied to this line, if any |
| `HasTax` / `RestaurantTaxValue` / `CategoryTaxValue` | Tax inputs and computed result |
| `ProfitPercentage` / `ProfitValue` | Internal margin tracking, not customer-visible |

## CartItemOptions
A further child of `CartItem` — one selected option (e.g. "extra cheese") at a quantity and price,
with its own `PriceChanged` flag mirroring the parent's. `CartItemOptions.Instance` is the only
construction path (`CartItemOptions.cs`, not read in full for this pass).

## Rule / Decision Matrix

One line in a customer cart — and the widest snapshot in the codebase: 40 properties, most of them copied from the restaurant, item and price at the moment of adding. Nothing here is validated; the entity is a record of what the customer saw.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | Everything about the item is snapshotted at add-to-cart | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:147` | `Instance` copies restaurant name and logo, item name and image, price name, tax and profit — so a later menu edit cannot change what the customer is looking at |
| 2 | No guard on any path | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:147` | Eight mutators, zero `Result` returns except `UpdateCartItemPrice`; the invariants live in the cart commands |
| 3 | A price change is flagged, not applied silently | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:115` | `MarkCartItemAsPriceChanging` sets `PriceChanged`, which is what lets checkout tell the customer |
| 4 | There is a second flag path for option-level changes | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:292` | `MarkCartItemAsPriceChangingWithOption` — same idea, separate method |
| 5 | `UpdateCartItemPrice` is the only method returning `Result` | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:121` | And it is the one that can change what the customer pays |
| 6 | Quantity changes carry no bounds | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:316` | `UpdateQuantity` assigns; zero or negative is the caller's problem |
| 7 | A tiered discount is attached to the line, and removable | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:338-343` | `SetTieredDiscount`/`RemoveTieredDiscount` — the per-line half of the cart-level lock |
| 8 | Offer discount is stored as both a value and a percentage flag | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:323` | `UpdateOfferDiscount` sets `OfferDiscount` alongside `IsOfferPercentage`, so the line records how the discount was expressed as well as its amount |
| 9 | Tax is captured at two levels | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:147` | `RestaurantTaxValue` and `CategoryTaxValue` both ride on the line |
| 10 | The restaurant's coordinates and capability flags are copied too | `Shared/TalabatkLogic/TalabatkModels/CartItem.cs:147` | `Restaurantlongitude`, `RestaurantLatitude`, `RestaurantHasUser`, `RestaurantHasDelivery` — so fee and assignment logic need not re-read the restaurant |

## Related
- [[CustomerCart.technical|CustomerCart]] — the owning cart and its mutation rules.
- [[CustomerCart.business|CustomerCart (business)]]
