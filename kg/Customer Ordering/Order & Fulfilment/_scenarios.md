---
id: 8orders/customer-ordering/order-and-fulfilment/scenarios
title: Order & Fulfilment — Scenario Catalog (Customer Ordering slice)
note_type: scenarios
context: Customer Ordering
feature: Order & Fulfilment
audience: Business · QA · Developer
sources:
  - path: Shared/TalabatkApplication/Commands/CancelOrderCommand/CancelOrderCommand.cs
    sha1: 1959b7a4f8c3
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
last_updated: 2026-08-02
---
# Order & Fulfilment — Scenario Catalog (Customer Ordering slice)

## Happy path
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| H1 | Repeat customer, single restaurant, cash, below the pending threshold | Checkout | Order starts `RestaurantPending`, goes straight to the restaurant | `Order.cs:2078-2094` |
| H2 | Order still in an early, unconfirmed state | Customer cancels | Order rejected/cancelled | `CancelOrderCommand.cs:71-90` |

## Partial / incremental
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| P1 | Order spans 2 restaurants | Checkout | Each restaurant gets its own `OrderRestaurantDetails` row + Daily Pickup Tag | `OrderRestaurantDetails.cs:104-` |

## Negative / guard
| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|--------------|--------|--------------------------------|-----------------|
| N1 | Neither cash, wallet, nor online amount provided | Checkout | Rejected — "Please select payment method." | `Order.cs:2338-2341` |
| N2 | Both cash and online amounts provided | Checkout | Rejected — "Cash payment cannot be combined with online payment." | `Order.cs:2312-2315` |
| N3 | Wallet-only payment, balance below order total | Checkout | Rejected — "you do not have enough Balanace in your Wallet" | `Order.cs:2317-2322` |
| N4 | Online amount sent by client differs from server-computed expected amount beyond tolerance | Checkout | Rejected — "Total Online Payment is Not Correct" (with diagnostic detail) | `Order.cs:2384-2395` |
| N5 | Order already rejected | Customer attempts to cancel again | Rejected — "Order is already rejected" | `CancelOrderCommand.cs:82` |
| N6 | Order already confirmed by the restaurant | Customer attempts to cancel | Rejected — localized `rejectAfterConfirmation` message | `CancelOrderCommand.cs:90` |
| N7 | Another customer's order id | Customer attempts to cancel it | Rejected — "Unauthorized" | `CancelOrderCommand.cs:77` |

## Returns / cancellation / reversal
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| R1 | Order still cancellable (see N5/N6) | `CancelOrder` | Order rejected | `CancelOrderCommand.cs` |

## Integration (cross-side / cross-context)
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| I1 | Order created | — | 3 domain events fire immediately: send notifications, calculate delivery time, calculate delivery method — consumed by handlers not documented in this pass | `Order.cs:2140-2142` |
| I2 | Order created that trips any risk signal (Rule 2) | — | Order starts `Pending` rather than going straight to the restaurant — presumably reviewed by Admin, not verified in this pass | `Order.cs:2078-2094` |

## Open Questions
- [ ] The full restaurant-confirmation, delivery-assignment, and delivery-completion scenario sets
  are out of scope for this pass — a future Restaurant Portal/Delivery pass should add them here,
  extending this same catalog rather than starting a new one for `Order`.
- [ ] Who/what actually reviews an order sitting in `Pending` status, and what happens if it's never
  reviewed, wasn't found in this pass.
