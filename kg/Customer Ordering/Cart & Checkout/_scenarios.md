---
id: 8orders/customer-ordering/cart-and-checkout/scenarios
title: Cart & Checkout — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Cart & Checkout
audience: Business · QA · Developer
sources:
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkLogic/TalabatkModels/CartItem.cs
    sha1: 7048d48ce442
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerCart.cs
    sha1: 1fddf55bade3
last_updated: 2026-08-02
---
# Cart & Checkout — Scenario Catalog

## Happy path
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| H1 | Empty cart | Add an item | Cart has 1 line, totals computed | `CustomerCart.cs:65-133` |
| H2 | Item already in cart | Add the identical item (same options/notes) again | Quantity merges into the existing line | `CustomerCart.cs:78-91` |
| H3 | Cart has items from restaurant A | Add an item from restaurant B, under the multi-restaurant cap | Cart now spans 2 restaurants | `CustomerCart.cs:266-270` |
| H4 | Valid cart, valid address/timing | Checkout with no promo/voucher | Order created | `CreateOrderFromCartCommand.cs:113-` |
| H5 | Valid cart | Checkout with a valid promo code meeting its minimum amount | Promo code discount applied | `CreateOrderFromCartCommand.cs:537-545` |

## Partial / incremental
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| P1 | Item in cart, its option price changes at the restaurant | Customer re-opens cart | Line flagged `PriceChanged`; event raised | `CustomerCart.cs:93-101, 121-130` |
| P2 | Cart item flagged `PriceChanged` | `UpdateCartItemPrices` called | Price refreshed, flag cleared, tax/profit recomputed | `CartItem.cs:121-145` |
| P3 | Existing cart item | `EditCartItem` changes it to match another existing line | The two lines silently merge (edit = remove + add) | `CustomerCart.cs:135-155` |

## Negative / guard
| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|--------------|--------|--------------------------------|-----------------|
| N1 | Cart has a `PriceChanged` item | Checkout | Rejected — must acknowledge/refresh first | `CreateOrderFromCartCommand.cs:147-150` |
| N2 | — | Checkout requests a scheduled delivery < minimum lead time, or outside working hours | Rejected | `CreateOrderFromCartCommand.cs:179-201` |
| N3 | Delivery area currently rush-time-busy | Checkout | Rejected — "All Restaurants are busy right now" | `CreateOrderFromCartCommand.cs:222-230` |
| N4 | Voucher already used | Checkout with that voucher | Rejected — "Voucher is used before" | `CreateOrderFromCartCommand.cs:305-307` |
| N5 | Merchant-scoped voucher, restaurant not in cart | Checkout with that voucher | Rejected — "Voucher cannot be applied to this order" | `CreateOrderFromCartCommand.cs:310-316` |
| N6 | Both `PromoCode` string and `VoucherId` supplied | Checkout | Voucher silently ignored — promo code path taken exclusively | `CreateOrderFromCartCommand.cs:272-289` |
| N7 | Cart at the multi-restaurant cap | Add an item from a new (not-already-in-cart) restaurant | Caller-level rejection (checked via `IsAllowedNumberOfRestaurantsPerOrderExceeded`, enforced by the calling command, not `CustomerCart` itself) | `CustomerCart.cs:266-270` |

## Returns / cancellation / reversal
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| R1 | Item in cart | `DeleteCartItem` | Line removed, totals recomputed | `CustomerCart.cs:210-220` |
| R2 | Cart has items | `ClearCustomerCart` | All lines removed | `CustomerCart.cs:261-264` |

## Integration (cross-side / cross-context)
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| I1 | Guest has a cart + locked discount + default address | Guest logs into an existing real account | Guest's cart/discount/address **replace** the real account's own (not merged); guest row is deleted only if there was something to merge | `MergeGuestCartIntoCustomerCommand.cs:78-162, 283-329` |
| I2 | Guest logs in, guest cart is empty/missing | Login completes | No-op merge; guest row deliberately left for the 24h purge job, not deleted here | `MergeGuestCartIntoCustomerCommand.cs:78-102` |
| I3 | Guest changed their "unavailable items" preference before logging in | Login/merge | Preference carries over to the real account | `MergeGuestCartIntoCustomerCommand.cs:401-444` |

## Open Questions
- [ ] No scenario found for what happens if two concurrent requests create a `CustomerCart` for the
  same brand-new customer at the same time — the missing unique index (see
  `CustomerCart.technical.md` conflicts) means this isn't proven safe.
- [ ] Where exactly the cart is cleared after a successful checkout wasn't confirmed in this pass.
