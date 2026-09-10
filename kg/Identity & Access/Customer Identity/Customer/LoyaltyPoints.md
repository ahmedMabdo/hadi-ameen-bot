---
id: 8orders/identity-and-access/customer-identity/loyaltypoints
note_type: single
rule_count: 8
context: Identity & Access
feature: Customer Identity
entity: LoyaltyPoints
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs
    sha1: 80209d2f6d29
last_updated: 2026-08-23
tags: [identity-access, customer, financial, child, technical, backend-domain]
---
# LoyaltyPoints

One ledger row per points-earning/expiry/redemption event for a [[Customer.technical|Customer]] —
already referenced from `Customer.AddEarnedLoyaltyPoints`/`AddExpirationLoyaltyPoints`/
`AddRedeemedLoyaltyPoints` (Customer.technical.md Rule 10), documented here to close that flagged gap.
`Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs`.

## Business rules
- **Validation is inconsistent across the three creation factories.** `AddEarnedPointsInstance`
  (`:26-52`) validates `orderId > 0` and `totalEarningPoints > 0`. `ExpiryPointsInstance` (`:54-71`)
  and `RedeemedPointsInstance` (`:73-93`) have **no validation at all** — a caller could construct an
  expiry/redemption row with a zero or negative point amount.
- **⚠️ Possible bug — `Redeem(requestedPoints)` has no guard against a negative input:**
  `:94-99` computes `redeemable = Math.Min(RemainingPoints, requestedPoints)` then
  `RemainingPoints -= redeemable`. If `requestedPoints` is negative, `redeemable` becomes that
  negative number (since it's less than a non-negative `RemainingPoints`), and subtracting a negative
  number **increases** `RemainingPoints` — the opposite of what "redeem" should ever do — while also
  returning a negative "amount redeemed" to the caller. Not confirmed whether any caller could ever
  pass a negative value in practice.
- `TransactionType` is a raw `int` (backed by `LoyaltyPointsTransactionTypeEnum` but not typed as the
  enum on this class) — same "polymorphic type stored as int" pattern seen elsewhere in this pass.
- `RedeemedPointsInstance`'s expiration date is `creationDate.AddDays(voucherExpirationDaysNumber)` —
  no guard against a negative `voucherExpirationDaysNumber`, which would produce an expiry date before
  the creation date.

## Rule / Decision Matrix

A batch of loyalty points: earned, expired or redeemed. Three named factories, and the partial-redemption arithmetic that makes a customer's balance auditable.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | Points are recorded in batches, not as a running total | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:26` | `AddEarnedPointsInstance` writes `Points` and `RemainingPoints` together, so partial spend is traceable to the batch it came from |
| 2 | Earning requires a real order | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:34` | "OrderId must be greater than zero." |
| 3 | Earned points must be positive | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:37` | "Points must be a positive value." |
| 4 | Expiry is a separate factory, and it is unguarded | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:54` | `ExpiryPointsInstance` returns `Result` with no failure path, so an expiry row need not reference an order |
| 5 | Redemption is a third factory, also unguarded | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:73` | `RedeemedPointsInstance` — the row that records points being spent |
| 6 | `Redeem` returns the amount actually taken | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:94` | A `decimal`, not a `Result` — so a caller that ignores the return value cannot tell a partial redemption from a full one |
| 7 | `ResetRemainingPoint` zeroes a batch outright | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:101` | `void`, no guard — used by expiry |
| 8 | A batch knows what it was spent on and what it came from | `Shared/TalabatkLogic/TalabatkModels/LoyaltyPoints.cs:26` | `UsedInTransaction` and `ResultedFromPoints` chain batches together; `Voucher` links the redemption to what it bought |

> The ledger of transfers between batches is `LoyaltyPointsSrc`, whose only guard is that the target is
> positive — see [[Customer Ordering/Discounts & Coupons/Discount-Resolution.technical|Discount Resolution]].

## Related
- [[Customer.technical|Customer]] — Rule 10, the three creation call sites

## Open Questions
- [ ] Whether `Redeem` is ever called with a caller-controlled (vs. internally-computed,
  presumably-always-non-negative) `requestedPoints` value.
- [ ] `LoyaltyPointsSrc`, `Vouchers` linkage (`UsedInTransaction`/`ResultedFromPoints`/`Voucher`
  properties) not traced in this pass.
