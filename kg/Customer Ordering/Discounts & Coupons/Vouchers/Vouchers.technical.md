---
id: 8orders/customer-ordering/discounts-and-coupons/vouchers-technical
note_type: technical
context: Customer Ordering
feature: Discounts & Coupons
entity: Vouchers
entity_type: legacy-poco-root
rule_count: 18
sources:
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Helper/LoyaltyPointsRedemptionErrors.cs
    sha1: 91821e5d1259
  - path: Shared/TalabatkLogic/TalabatkModels/Vouchers.cs
    sha1: 70ea6dc0ea9a
last_updated: 2026-08-23
tags: [customer-ordering, discounts-coupons, transactional, technical, backend-domain]
---
# Vouchers — Technical

> **Layer:** Domain — Legacy POCO (plain public setters via `{ get; private set; }`, no event support found)   **Context:** Customer Ordering   **Feature:** Discounts & Coupons
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Vouchers.cs`   **Last Updated:** 2026-08-02

Store credit created by redeeming loyalty points — selected by id at checkout, not typed as a code.
Distinct from [[PromoCodes.technical|PromoCodes]] (see that note's "Resolving
CONTEXT.md's Coupon ambiguity" section) despite heavy naming overlap in the codebase.

## Business Rules

### Rule 1: A voucher's discount amount is derived from a points-redemption rate, not entered directly
- **Plain language:** Redeeming loyalty points into a voucher computes the cash discount from a
  rate: how much money a given number of points is worth.
- **Source:** `Vouchers.cs:44-77` (`Instance`) — `discountAmount = redeemingPointsMoney /
  redeemingPointsNumber * pointsToRedeem`. Guards: `userId > 0`, `voucherCode` required,
  `pointsToRedeem > 0`.
- **Expiry:** `ExpiryDate = createdDate.AddDays(expiryDays)` — a configurable window from issuance,
  not a fixed calendar date like `PromoCodes`/`TieredDiscount`.

### Rule 2: Optional merchant-scoping is applied *after* creation, as a separate step
- **Plain language:** A voucher can later be tied to a specific merchant, with the merchant
  absorbing a percentage of the discount — this isn't part of initial issuance, it's a follow-up
  call.
- **Source:** `Vouchers.cs:80-88` (`ApplyMerchantLoyaltyAtIssue`) — no-ops silently if
  `merchantId <= 0` (does not return a `Result.Failure`, unlike most guards elsewhere in this
  codebase — see Open Questions). Rounds `MerchantDiscountContribution` with
  `MidpointRounding.AwayFromZero`, a different rounding mode than the `Math.Round` (banker's
  rounding, .NET default) used everywhere else in `TieredDiscount`/`PromoCodes`.

### Rule 3: State is simpler than PromoCodes' — only used/expired/available
- **Source:** `Vouchers.cs:34-43` (`GetVoucherState`) — no budget cap, no per-customer usage cap
  (a voucher belongs to exactly one customer, `UserId`, from issuance — there's no "how many times
  can this customer use it" question the way there is for a shared `PromoCodes` code).

### Rule 4: Usage is a simple boolean flip, not a counter
- **Source:** `Vouchers.cs:90-97` (`MakeVoucherUsed`/`MakeVoucherUnused`) — contrast with
  `PromoCodes.UseVoucher`/`UnuseVoucher`, which increment/decrement a shared counter and budget
  across all customers. A `Vouchers` row is single-use by construction (one customer, one flag).

### Rule 5: Merchant-scoped minimum order check happens at checkout, not on the voucher itself
- **Source:** `CreateOrderFromCartCommand.cs:507-529` (documented in `CustomerCart.technical.md`
  Rule 9.12) — `Vouchers` itself has no method enforcing `MinOrderAmountAtIssue`; the checkout
  handler reads the field and does the comparison inline.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `Id` | PK | — (only entity in this pass with a **public** setter on its key, `{ get; set; }` not `{ get; private set; }` — see Open Questions) |
| `UserId` | The one customer this voucher belongs to | required at creation |
| `VoucherCode` | A code string on the voucher | required at creation, but redemption is by `Id`, not by typing this (see `CartController.ValidateVoucher(int voucherId, ...)`) |
| `PointsRedeemed` | How many loyalty points were spent to create this | > 0 |
| `DiscountAmount` | The resulting cash value | derived, not settable after creation (no setter method found) |
| `IsUsed` | Single-use flag | default `false` |
| `LoyaltyPointsId` / `LoyaltyPoints` | Link to the source redemption | full `LoyaltyPoints` entity not documented in this pass (see Customer Account feature — redeemed via `CustomerUserController.RedeemPoints`/`RedeemPointsWithMerchant`, **not** `IRecycleRedeems`, an unrelated external recycling-program wallet-credit integration) |
| `MerchantId` / `MerchantDiscountContribution` / `MinOrderAmountAtIssue` | Optional merchant-scoping, applied post-creation | all nullable; only set via `ApplyMerchantLoyaltyAtIssue` |

## Status / State
`GetVoucherState(now)` → `VoucherStateEnum.Used` (if `IsUsed`) → `Expired` (if past `ExpiryDate`) →
`Available`. Simpler than `PromoCodes.GetState`, which also folds in budget/usage-cap checks.

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `LoyaltyPoints` | Backend-Domain (legacy POCO, not yet documented) | `LoyaltyPointsId` FK | The redemption source; see `IRecycleRedeems` controller (Batch 5, not yet documented) and `LoyaltyPointsRedemptionErrors.cs` (Application-layer error keys found during repo mapping). |
| `Restaurant` (as `MerchantRestaurant`) | Backend-Domain (legacy POCO) | `MerchantId` FK, `DeleteBehavior.NoAction` | No cascade and no set-null — deleting a restaurant with vouchers scoped to it would need to be handled explicitly elsewhere (not verified). |
| `Order` | Backend-Domain (legacy POCO) | `Order` navigation property | Set when the voucher is consumed at checkout. |
| [[PromoCodes.technical\|PromoCodes]] | Backend-Domain (legacy POCO) | Mutually exclusive at checkout | See `CustomerCart.technical.md` Rule 9.9. |

## Rule / Decision Matrix
| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|-----------------|---------------------|---------|--------|
| 1 | Issue (redeem points) | `pointsToRedeem <= 0` | rejected | `Vouchers.cs:60-61` |
| 2 | Checkout | Voucher not found / doesn't belong to requesting customer | rejected — "Voucher is not valid" | `CreateOrderFromCartCommand.cs:294-301` |
| 3 | Checkout | `IsUsed = true` | rejected — "Voucher is used before" | `CreateOrderFromCartCommand.cs:305-307` |
| 4 | Checkout | Merchant-scoped, restaurant not in cart | rejected | `CreateOrderFromCartCommand.cs:310-316` |
| 5 | Checkout (post-order-creation) | Resulting subtotal below `MinOrderAmountAtIssue` | rejected | `CreateOrderFromCartCommand.cs:507-529` |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 3 | `LoyaltyPoints` (source), `Restaurant` (optional scope), `Order` (consumption) |
| Sides touched | 3/5 | Backend-Domain, Backend-Application, Backend-Data |
| Cross-context integrations | 0 confirmed | Loyalty-points issuance path not verified in this pass |
| Domain events involved | 0 confirmed | No `AddEvent`/base-class event support found on this class (contrast with `PromoCodes`, `CustomerCart`) |
| Hub? | no | |

## Open Questions
- [ ] `Id` is the only primary key in this pass's coverage with a public setter — confirm whether
  that's intentional (e.g. EF requires it for some scenario) or an oversight relative to the
  private-setter convention `.cursor/rules/DOMAIN_ENTITY_ACCESS_RULES.mdc` establishes elsewhere.
- [ ] `ApplyMerchantLoyaltyAtIssue` silently no-ops on an invalid `merchantId <= 0` instead of
  returning a `Result.Failure` — inconsistent with the `Result`-based guard style used everywhere
  else in this codebase; confirm this is deliberate (e.g. a genuinely optional call site) rather
  than a copy-paste gap.
- [ ] The rounding mode mismatch (`MidpointRounding.AwayFromZero` here vs. plain `Math.Round`,
  banker's rounding, in `TieredDiscount`/`PromoCodes`) could produce a one-cent discrepancy between
  discount mechanisms on the same order total — not confirmed as user-visible, flagged for
  awareness.
- [ ] Full `LoyaltyPoints` entity and the loyalty-points-earning side were not documented in this
  pass — see the Customer Account feature (`RedeemingLoyaltyPointsCommand`).

## Related
- Business view: [[Vouchers.business|Vouchers]]
- [[PromoCodes.technical|PromoCodes]] — the other checkout-time discount mechanism
- [[TieredDiscount.technical|TieredDiscount]] — the third, auto-applied mechanism
