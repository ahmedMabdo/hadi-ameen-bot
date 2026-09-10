---
id: 8orders/customer-ordering/discounts-and-coupons/promocodes-technical
note_type: technical
context: Customer Ordering
feature: Discounts & Coupons
entity: PromoCodes
entity_type: legacy-poco-root
rule_count: 25
sources:
  - path: Shared/TalabatkApplication/Commands/AddVoucherCommand/AddVoucherCommand.cs
    sha1: ea70b0433034
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/SaveEditPromoCodeCommand/SaveEditPromoCodeCommand.cs
    sha1: 26dfd80ac959
  - path: Shared/TalabatkData/Mapping/PromoCodeMap.cs
    sha1: 58b0e446e217
  - path: Shared/TalabatkLogic/TalabatkModels/PromoCodes.cs
    sha1: f8280d78440d
  - path: TalabatkAPIs/Controllers/Vouchers/VouchersController.cs
    sha1: c002b37bae65
last_updated: 2026-08-23
tags: [customer-ordering, discounts-coupons, transactional, technical, backend-domain]
---
# PromoCodes — Technical

> **Layer:** Domain — Legacy POCO, event-raising (extends the shared `entity` base, same as `CustomerCart`)   **Context:** Customer Ordering (consumption) / Admin (management, inferred, not verified in this pass)   **Feature:** Discounts & Coupons
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/PromoCodes.cs`   **Last Updated:** 2026-08-02

A manually-entered discount code a customer types in at checkout (`Promo` string) — distinct from
[[TieredDiscount.technical|TieredDiscount]] (auto-applied,
no code) and [[Vouchers.technical|Vouchers]] (issued from redeeming loyalty points,
selected by id not typed). See "Resolving CONTEXT.md's Coupon ambiguity" below.

## Business Rules

### Rule 1: Creation validation (newer factory only — see Conflicts)
- **Source:** `PromoCodes.cs:182-224` (`Instance_V1`) — start/expiry date not in the past (with a
  1-day grace via `creationDate.Date.AddDays(-1)`), start ≤ expiry, discount value > 0, minimum
  amount ≥ 0, budget limit > 0, merchant contribution ≤ 100, and for a **fixed-value** code the
  `MaximumValue` must equal the discount value exactly.
- The **legacy** factory (`Instance`, `PromoCodes.cs:102-152`) has **no validation at all** — same
  old-vs-new pattern seen in Tiered Discount and elsewhere in this codebase.

### Rule 1a: Application-layer caller can crash before Rule 1 ever runs
- **⚠️ Confirmed bug:** `AddVoucherCommand.Handle` calls `request.EnglishName.Trim()` and
  `request.ArabicName.Trim()` (`:63-64`) **before** any null-check on those fields (the only earlier
  guard is for `Promo`) — a request with a null `EnglishName`/`ArabicName` throws
  `NullReferenceException` instead of a graceful `Result.Failure`, never reaching `Instance_V1`'s own
  validation (Rule 1). Same "trim before null-check" shape as `_conflicts.md` #15
  (`DeliverySupplier.Instance`).
- **Source:** `AddVoucherCommand.cs:63-64`.

### Rule 1b: `SaveEditPromoCodeCommand` can silently corrupt a code's dates instead of rejecting them
- **⚠️ Confirmed bug:** `SaveEditPromoCodeCommand.Handle` calls `DateTime.TryParseExact` for both
  `CreationDate` and `ExpiryDate` without checking the returned `bool` — a malformed date string
  silently becomes `DateTime.MinValue` and is passed straight into `Update(...)`, so the promo code's
  start/expiry date silently corrupts to year 0001 instead of the request failing with a validation
  error. Worse than a crash: nothing here throws, so the wrapping try/catch never even sees it — bad
  data is saved with no error surfaced to the caller at all.
- **Source:** `SaveEditPromoCodeCommand.cs:40-41`.

### Rule 2: Merchant + company contribution is a computed complement, not two independent fields
- **Plain language:** Unlike Tiered Discount (which stores both percentages and validates they sum
  to 100), PromoCodes only stores `MerchantContributionPercentage` — `CompanyContributionPercentage`
  is a read-only computed property (`100 - MerchantContributionPercentage`), so they can never
  disagree by construction.
- **Source:** `PromoCodes.cs:49-50`.

### Rule 3: Redemption eligibility gauntlet
- **Source:** `PromoCodes.cs:459-517` (`ValidatePromoCode`), each a distinct rejection reason
  (`PromoCodeStatus` enum): date window (`Expiration`), usage cap (`EndUseTimes`, only if
  `NumberOfUse > 0` — default is `int.MaxValue`, i.e. unlimited unless explicitly capped), budget cap
  (`BudgetExceeded`), area restriction (`NotSupportedArea`), new-customer-only
  (`NewCustomerOnly` — only blocks if the customer **has** a delivered order **and** has used this
  code 0 times before), per-customer usage cap (`ExceedNumberOfUsageForCustomer`), restaurant
  restriction (`NotSupportedRestaurant`), and minimum order amount (`MinimumValueNotMet`).

### Rule 4: Discount calculation differs by type and restaurant scope
- **Plain language:** A `DeliveryDiscount` code discounts the delivery fee only, capped at both
  `MaximumValue` and the actual delivery fee. An `ItemDiscount` code with no restaurant scope applies
  to the whole order's item subtotal; scoped to specific restaurants, it applies only to those
  restaurants' subtotal.
- **Source:** `PromoCodes.cs:395-456` (`CalculatePromoCodeDiscount`, `CalculateDiscount`).

### Rule 5: Usage/budget tracking uses "Voucher"-named methods
- **Source:** `PromoCodes.cs:532-542` — `UseVoucher(decimal amount)` increments `NumberOfTimesUsed`
  and `BudgetSpent`; `UnuseVoucher` reverses both. Despite the class being `PromoCodes`, its own
  usage-tracking methods are named after "Voucher" — see Conflicts.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `Promo` | The code text the customer types | max length 50 (`[StringLength(50)]`), **no DB uniqueness constraint** — see Conflicts |
| `Type` | `ItemDiscount` or `DeliveryDiscount` (`PromoCodeType` enum) | int-backed, not a true enum column |
| `NumberOfUse` | Total redemption cap across all customers | defaults to `int.MaxValue` (effectively unlimited) |
| `MaximumTimeUsedForOneCustomer` | Per-customer redemption cap | DB default `1` (`PromoCodeMap.cs:17`) |
| `NewCustomerOnly` | Restrict to customers with no delivered order yet | default `false` |
| `BudgetLimit` / `BudgetSpent` | Campaign spend cap and running total | `BudgetLimit <= 0` fails creation (Rule 1) |
| `MerchantContributionPercentage` | Restaurant's share of cost | company share is the complement (Rule 2) |
| `CombineWithOffers` | Whether it can stack with a restaurant's own item-level offer | — |
| `PromoCodeAreas` / `PromoCodeCities` / `RestaurantPromoCodes` / `PromoCodeCustomers` / `PromoCodeAudiences` | Optional targeting scopes | empty = unrestricted for that dimension, same pattern as `TieredDiscount`'s allow-lists |

## Status / State
`Active` (bool) plus date window plus budget/usage caps jointly determine redeemability —
`GetState(now, usedCountByCustomer)` (`PromoCodes.cs:544-560`) derives a `VoucherStateEnum`
(`Used` / `Expired` / `Available`) — note this reuses the **same enum type** as `Vouchers`
(`VoucherStateEnum`), another instance of the Voucher/PromoCode naming overlap.

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `Order` | Backend-Domain (legacy POCO) | `TA_Orders` collection, read at checkout | Checked/applied inside `CreateOrderFromCartCommand` (see `CustomerCart.technical.md` Rule 9.9). |
| `Restaurant`, `Customer`, `Audiance`, `PromoCodeArea`/`PromoCodeCity` | Backend-Domain (legacy POCO) | Optional targeting join tables | Same allow-list pattern as `TieredDiscount`. |
| [[Vouchers.technical\|Vouchers]] | Backend-Domain (legacy POCO) | Mutually exclusive at checkout, not a data relationship | A checkout request supplies either `PromoCode` (string) or `VoucherId` (int), never both meaningfully — see `CustomerCart.technical.md` Rule 9.9. |

> ⚠️ **CONFLICT/GAP — No DB uniqueness constraint on the promo code text**
> `PromoCodeMap.cs` sets no `HasIndex(x => x.Promo).IsUnique()`. Every redemption lookup found
> (`CreateOrderFromCartCommand.cs:273-288`) matches on `p.Promo.Trim() == request.PromoCode.Trim()`
> via `FirstOrDefaultAsync` — if two active codes ever shared the same text, one would silently and
> arbitrarily shadow the other. **This is the same systemic pattern already flagged for
> `CustomerCart.CustomerId`** (see `_system/_conflicts.md`) — worth treating as a repo-wide theme
> (uniqueness enforced by application convention, not the schema) rather than three unrelated bugs.

> ⚠️ **NOTE — Deep terminology conflation between "PromoCode" and "Voucher" in the code itself, not just docs**
> `TalabatkAPIs/CONTEXT.md` already flags "Coupon" as ambiguous across three entities. This pass
> found the conflation runs *into the code*, not just user-facing language: `PromoCodes.Instance_V1`
> raises a `VoucherCreatedEvent` (`PromoCodes.cs:258-268`) on **promo code** creation; `PromoCodes`'s
> own usage-tracking methods are literally named `UseVoucher`/`UnuseVoucher` (Rule 5); and both
> classes share the same `VoucherStateEnum`. `VouchersController.CheckCustomerVouchers` even accepts
> a `promo` string parameter (`VouchersController.cs:73-81`, `CheckCustomerVouchersQuery`), further
> blurring the boundary at the API surface. **Resolving CONTEXT.md's Coupon ambiguity, as far as
> this pass can tell:** `PromoCodes` = a manually-typed code string, admin-configured, targetable by
> area/city/restaurant/customer/segment, with a budget cap. `Vouchers` = issued automatically from
> redeeming loyalty points (see `Vouchers.technical.md`), selected by id, not typed. `TieredDiscount`
> = auto-applied spend-tier campaign, no code or selection at all. This is inferred from the code
> read in this pass, not confirmed with the product team — flagged as an Open Question, not asserted
> as final.

## Rule / Decision Matrix
| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|-----------------|---------------------|---------|--------|
| 1 | Create (`Instance_V1`) | start/expiry date in the past (beyond 1-day grace) | rejected | `PromoCodes.cs:185-193` |
| 2 | Create (`Instance_V1`) | fixed-value code where `MaximumValue != DiscountValue` | rejected | `PromoCodes.cs:221-224` |
| 3 | Redeem | `now` outside `[StartDate, ExpiryDate]` | rejected — `Expiration` | `PromoCodes.cs:471-474` |
| 4 | Redeem | `NumberOfTimesUsed >= NumberOfUse` (and capped) | rejected — `EndUseTimes` | `PromoCodes.cs:476-479` |
| 5 | Redeem | `BudgetSpent >= BudgetLimit` (and capped) | rejected — `BudgetExceeded` | `PromoCodes.cs:481-484` |
| 6 | Redeem | Customer has a delivered order and 0 prior uses of this code, code is new-customer-only | rejected — `NewCustomerOnly` | `PromoCodes.cs:492-498` |
| 7 | Redeem | Per-customer usage at/above cap | rejected — `ExceedNumberOfUsageForCustomer` | `PromoCodes.cs:500-503` |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 6+ | `Order`, `Restaurant`, `Customer`, `Audiance`, `PromoCodeArea`/`City` join tables |
| Sides touched | 3/5 | Backend-Domain, Backend-Application, Backend-Data |
| Cross-context integrations | 0 confirmed | Management path (likely Admin, mirroring Tiered Discount) not verified in this pass |
| Domain events involved | 1 | `VoucherCreatedEvent` (misleadingly named — raised by PromoCode creation) |
| Hub? | no | Bounded to Discounts & Coupons + read at Cart & Checkout |

## Open Questions
- [ ] Where PromoCodes are created/managed (which host — presumably Admin, mirroring Tiered
  Discount) was not verified in this pass; only the customer-facing read/redeem side was confirmed.
- [ ] The `PromoCode`/`Voucher` naming conflation theory above should be confirmed with the team
  before treating it as authoritative — it's a strong inference from multiple independent code
  signals, not a direct statement found anywhere.
- [ ] `PromoCodeType` is stored as a plain `int` (`Type` property), not a strongly-typed enum column
  — confirm this isn't a source of silent bugs if the enum's underlying values ever get renumbered.

## Related
- Business view: [[PromoCodes.business|PromoCodes]]
- [[Vouchers.technical|Vouchers]] — the other checkout-time discount mechanism
- [[TieredDiscount.technical|TieredDiscount]] — the third, auto-applied mechanism
- Business-term background: [[../../../../../Talabatk.IDS/CONTEXT|Customer Ordering CONTEXT.md]] ("Coupon" ambiguity, Discounts & coupons section)
