---
id: 8orders/customer-ordering/discounts-and-coupons/scenarios
title: Discounts & Coupons — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Discounts & Coupons
audience: Business · QA · Developer
sources:
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkLogic/TalabatkModels/PromoCodes.cs
    sha1: f8280d78440d
  - path: Shared/TalabatkLogic/TalabatkModels/Vouchers.cs
    sha1: 70ea6dc0ea9a
last_updated: 2026-08-02
---
# Discounts & Coupons — Scenario Catalog

## Happy path
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| H1 | Valid, active promo code, order meets minimum | Checkout with the code | Discount applied per type (item/delivery) | `PromoCodes.cs:395-456` |
| H2 | Customer has enough loyalty points | Redeem into a voucher | Voucher created with computed discount amount | `Vouchers.cs:44-77` |
| H3 | Customer has an available, unused voucher | Checkout, select it | Discount applied, voucher marked used | `Vouchers.cs:90-93` |

## Partial / incremental
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| P1 | Voucher issued without a merchant | Later scoped to a merchant via `ApplyMerchantLoyaltyAtIssue` | Merchant contribution computed; silently no-ops if `merchantId <= 0` | `Vouchers.cs:80-88` |

## Negative / guard
| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|--------------|--------|--------------------------------|-----------------|
| N1 | Promo code past its expiry/start window | Checkout with it | Rejected — `Expiration` | `PromoCodes.cs:471-474` |
| N2 | Promo code at its total or per-customer usage cap | Checkout with it | Rejected — `EndUseTimes` / `ExceedNumberOfUsageForCustomer` | `PromoCodes.cs:476-479, 500-503` |
| N3 | Promo code budget exhausted | Checkout with it | Rejected — `BudgetExceeded` | `PromoCodes.cs:481-484` |
| N4 | New-customer-only code, customer has a delivered order and never used this code | Checkout with it | Rejected — `NewCustomerOnly` | `PromoCodes.cs:492-498` |
| N5 | Voucher already used | Checkout with it | Rejected — "Voucher is used before" | `CreateOrderFromCartCommand.cs:305-307` |
| N6 | Merchant-scoped voucher, that merchant not in cart | Checkout with it | Rejected — "Voucher cannot be applied to this order" | `CreateOrderFromCartCommand.cs:310-316` |
| N7 | Both a promo code string and a voucher id supplied | Checkout | Voucher silently ignored; promo code path taken | `CreateOrderFromCartCommand.cs:272-289` |
| N8 | Resulting order/merchant subtotal below the promo code's/voucher's minimum amount | Checkout completes order creation | Rejected even after the Order was tentatively built | `CreateOrderFromCartCommand.cs:507-545` |

## Returns / cancellation / reversal
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| R1 | Order using a promo code is cancelled/reversed | `UnuseVoucher` called on the `PromoCodes` row | Usage count and budget spent both decremented | `PromoCodes.cs:538-542` |
| R2 | Order using a voucher is cancelled/reversed | `MakeVoucherUnused` called | `IsUsed` reset to false | `Vouchers.cs:95-97` |

## Integration (cross-side / cross-context)
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| I1 | — | Checkout (cross-feature: Cart & Checkout) | Promo Code and Voucher are read and validated inside `CreateOrderFromCartCommand`, not owned by `CustomerCart` itself | See `CustomerCart.technical.md` Rule 9.9, 9.12, 9.13 |

## Open Questions
- [ ] No scenario found for what a customer sees if a promo code AND a voucher are both "valid" but
  only one is used — confirm the UI actually presents this as an either/or choice, matching the
  backend's silent voucher-ignored behavior (N7), rather than looking like a bug.
- [ ] Loyalty points **earning** (as opposed to redemption) is out of scope for this pass — see Batch 5.
