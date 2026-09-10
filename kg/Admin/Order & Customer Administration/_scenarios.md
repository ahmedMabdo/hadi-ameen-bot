---
id: 8orders/admin/order-and-customer-administration/scenarios
title: Order & Customer Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: Order & Customer Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Controllers/Order/OrderController.cs
    sha1: 934f4250495d
  - path: AdminUi/Controllers/CustomerController/CustomerController.cs
    sha1: 54a6cd2065b5
  - path: AdminUi/Controllers/PromoCodeController/PromoCodeController.cs
    sha1: af582ae3ea2c
  - path: AdminUi/Controllers/VoucherController/VoucherController.cs
    sha1: 5baa40ef4fde
tags: [admin, order-and-customer-administration, scenarios]
---
# Order & Customer Administration — Scenario Catalog

> Almost every row is an **override** of a decision another part of the system already made. That is why
> the authorisation rows matter here more than the count of endpoints suggests.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Operations need to find an order | `GET api/Order/GetOrderByStatus` | Orders in that status — permission-gated | `AdminUi/Controllers/Order/OrderController.cs:121` |
| H2 | Order stuck with an unavailable driver | `POST api/Order/SwapDeliveryMan` | Reassigned to another driver | `AdminUi/Controllers/Order/OrderController.cs:295` |
| H3 | Order confirmed in error | `POST api/Order/UnConfirmOrder` | Returned to the pre-confirmation state | `AdminUi/Controllers/Order/OrderController.cs:435` |
| H4 | Something needs recording against a delivery | `POST api/Order/AddNewDeliveryComment` | Comment stored | `AdminUi/Controllers/Order/OrderController.cs:510` |
| H5 | Customer owed their money back | `POST api/Order/Refund` | Reversal executed; the staff member's name stamped for audit | `AdminUi/Controllers/Order/OrderController.cs:169-170` |
| H6 | Merchant settlement wrong | `POST api/Order/FixMerchantStatement` | Settlement rows rewritten | `AdminUi/Controllers/Order/OrderController.cs:365` |
| H7 | Customer calls support | `GET api/Order/GetCustomerOrderHistory` | Their order history | `AdminUi/Controllers/Order/OrderController.cs:536` |
| H8 | Marketing launches a campaign | promo code created | Available to customers at checkout | `AdminUi/Controllers/PromoCodeController/PromoCodeController.cs` |
| H9 | Same, voucher-based | voucher created | Available to redeem | `AdminUi/Controllers/VoucherController/VoucherController.cs` |
| H10 | Support tops up a wallet | reason chosen from the catalogue | Adjustment categorised | `AdminUi/Controllers/WalletTransactionRechargeReasonController/WalletTransactionRechargeReasonController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Payment authorised but not captured | `POST api/Order/Refund` | Executed as a **void**; the response value is `true` to say so | `AdminUi/Controllers/Order/OrderController.cs:177-179` |
| P2 | Payment already captured | `POST api/Order/Refund` | Executed as a genuine **refund**; response value distinguishes it | `AdminUi/Controllers/Order/OrderController.cs:177-179` |
| P3 | Multi-restaurant order, one portion wrong | fix that portion's settlement | Statement rows are per restaurant portion | [[Merchant-Accounting-and-Order-Cost\|Merchant Accounting & Order Cost]] |
| P4 | Customer has many tags | `GET api/Order/CustomerTags` | All tags for that customer id | `AdminUi/Controllers/Order/OrderController.cs:560` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Not signed in | any action in this feature | 401 — class-level `[Authorize]` | `AdminUi/Controllers/Order/OrderController.cs:82` |
| N2 | Signed in without the order permission | `GET api/Order/GetOrderByStatus` | Denied — this one is gated | `AdminUi/Controllers/Order/OrderController.cs:121` |
| N3 | Signed in without any particular permission | `POST api/Order/Refund` | **Allowed** — no permission attribute | 🔴 `AdminUi/Controllers/Order/OrderController.cs:169` · #622 |
| N4 | Same | `POST api/Order/FixMerchantStatement` | **Allowed** | 🔴 `AdminUi/Controllers/Order/OrderController.cs:365` · #622 |
| N5 | Refund attempted twice | second call | Gateway-side behaviour not traced — treat as unverified | `AdminUi/Controllers/Order/OrderController.cs:169` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Refund issued in error | — | No un-refund; a new charge would be required | `AdminUi/Controllers/Order/OrderController.cs:169` |
| R2 | Statement fixed wrongly | fix again | The action rewrites rather than appends | `AdminUi/Controllers/Order/OrderController.cs:365` |
| R3 | Driver swapped in error | swap again | Reversible | `AdminUi/Controllers/Order/OrderController.cs:295` |
| R4 | Order un-confirmed in error | confirm again | Handled by the merchant side | [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] |
| R5 | Promo code launched in error | deactivate it | Effect on carts already built is untraced | `AdminUi/Controllers/PromoCodeController/PromoCodeController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Refund executed | payment gateway | Void or refund at the gateway; a dedicated journal builder posts the accounting side | `GlApiService.RefundedOnlinePayments.cs`; `_integrations.md` row 20 |
| I2 | Statement fixed | GL batch | The corrected rows are what get posted | `_integrations.md` row 20 |
| I3 | Driver swapped | driver apps | Both drivers' assigned lists change | [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] |
| I4 | Order un-confirmed | merchant dashboard | The store sees it return to its queue | [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] |
| I5 | Promo code or voucher created | customer checkout | Redemption rules live on the entities | [[PromoCodes.technical\|PromoCodes]], [[Vouchers.technical\|Vouchers]] |
| I6 | Support notification | Tawk.to | `SendTawkToNotificationToCustomer` / `…ToRestaurant` push a support nudge | `AdminUi/Controllers/Order/OrderController.cs:585`, `:604` |

## Authorisation scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Any signed-in back-office user | `POST api/Order/Refund` | **A customer's online payment is reversed.** Only the user name is recorded | 🔴 #622 · `AdminUi/Controllers/Order/OrderController.cs:169` |
| X2 | Same | `POST api/Order/FixMerchantStatement` | A restaurant's settlement rows are rewritten | 🔴 #622 · `AdminUi/Controllers/Order/OrderController.cs:365` |
| X3a | Same | `POST api/Order/SwapDeliveryMan` | A live order is reassigned to another driver | 🔴 #622 · `AdminUi/Controllers/Order/OrderController.cs:295` |
| X3b | Same | `POST api/Order/UnConfirmOrder` | A confirmed order is moved back a step | 🔴 #622 · `AdminUi/Controllers/Order/OrderController.cs:435` |
| X4 | Same | `GET api/Order/GetCustomerOrderHistory?customerId=<any>` | Any customer's order history | 🔴 #622 · `AdminUi/Controllers/Order/OrderController.cs:536` |
| X5 | Reconciling refunds | read the response | `true` means the reversal was a **void**, not a refund — the two settle differently | ⚠️ `AdminUi/Controllers/Order/OrderController.cs:177-179` |

## Open Questions

- [ ] Should `Refund` and `FixMerchantStatement` require a permission (X1, X2)? Their siblings do.
- [ ] Is there any approval step, value limit or reason field for a refund? Only a user name is recorded.
- [ ] What happens on a duplicate refund attempt (N5)?
- [ ] Does the refund reconcile automatically against the refund journal, or is that manual?
- [ ] Do promo-code or voucher changes affect carts already built (R5)?
- [ ] What customer fields does `CustomerController`'s Excel export include, and is it gated?
