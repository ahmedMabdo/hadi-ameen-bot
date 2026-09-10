---
id: 8orders/customer-ordering/tiered-discount/tiereddiscount-technical
note_type: technical
context: Customer Ordering
feature: Tiered Discount
entity: TieredDiscount
entity_type: aggregate-root
rule_count: 54
sources:
  - path: AdminUi/ClientApp/src/app/Tiered-Discount/add-tiered/add-tiered.component.ts
    sha1: 043ba9fc322f
  - path: AdminUi/Controllers/TieredDiscountController/TieredDiscountController.cs
    sha1: 62614ed5fb65
  - path: Shared/TalabatkApplication/Commands/EditTieredDiscountCommand/EditTieredDiscountCommand.cs
    sha1: da39a3ee5e6b
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs
    sha1: 6b071f1b5edb
  - path: Shared/TalabatkApplication/TieredDiscounts/Commands/AddTieredDiscount/AddTieredDiscountCommandValidator.cs
    sha1: 03a1019d9766
  - path: Shared/TalabatkApplication/TieredDiscounts/Commands/UpdateTieredDiscountActivityCommand/UpdateTieredDiscountActivityCommand.cs
    sha1: a9cd6bb31d01
  - path: Shared/TalabatkApplication/TieredDiscounts/Queries/GetVoucherByIdQuery/GetTieredDiscountByIdQuery.cs
    sha1: 99dbba93233e
  - path: Shared/TalabatkData/Mapping/TieredDiscountConfigurations/TieredDiscountMap.cs
    sha1: e127780ffdda
  - path: Shared/TalabatkData/Migrations/20250103000001_AddTieredDiscountIdToCartItem.cs
    sha1: eea62e123801
  - path: Shared/TalabatkData/Migrations/20260715150740_GuestModeCart.cs
    sha1: 6f347e0a46ef
  - path: Shared/TalabatkLogic.Test/CustomerCartCases/CustomerCartLockedDiscountTests.cs
    sha1: 70c8e1e5992b
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/POCOs/TieredDiscountTierPoco.cs
    sha1: 26472503da0e
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscount.cs
    sha1: 5a01e502c2ef
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs
    sha1: 3a2304c31451
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTypeEnum.cs
    sha1: c065dace1402
last_updated: 2026-08-23
tags: [customer-ordering, tiered-discount, transactional, technical, backend-domain]
---
# TieredDiscount — Technical

> **Layer:** Domain — Aggregate Root (one of only 4 real DDD aggregates in the codebase)   **Context:** Customer Ordering (consumption) / Admin (management)   **Feature:** Tiered Discount
> **Source Path:** `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscount.cs`   **Last Updated:** 2026-08-02

A restaurant-level discount that rewards a customer with a bigger discount the more they spend,
in configurable tiers (e.g. "spend 200 EGP get 10% off, spend 400 EGP get 15% off"). Can target
specific customers, customer segments ("audiences"), specific restaurants, or be open to everyone —
including, since a 2026 change, guests who haven't logged in yet.

## Business Rules

### Rule 1: Required identity fields
- **Plain language:** A tiered discount must have an internal code and both Arabic and English names.
- **Trigger:** Creation.
- **Violation result:** `Result.Failure("Internal code is required")` / `"Arabic name is required"` / `"English name is required"`.
- **Source:** `TieredDiscount.cs:206-213` (`Validate`).

### Rule 2: Delivery discount can't be percentage-based
- **Plain language:** A delivery-fee discount must be a fixed amount, never a percentage.
- **Trigger:** Creation.
- **Violation result:** `Result.Failure("Delivery discount can only be fixed value")`.
- **Source:** `TieredDiscount.cs:215-216`.

### Rule 3: Maximum discount value must be positive
- **Source:** `TieredDiscount.cs:218-219` — `Result.Failure("Maximum discount value must be greater than 0")`.

### Rule 4: Merchant + 8Order contribution must sum to exactly 100%
- **Plain language:** The discount's cost is split between the restaurant and 8Order; the two
  percentages must add up to exactly 100 — there's no case where 8Order or the restaurant absorbs
  more/less than the other doesn't cover.
- **Trigger:** Creation.
- **Violation result:** `Result.Failure("Sum of Merchant and 8Order contribution percentages must equal 100%")` (and each side individually must be within `[0, 100]`).
- **Source:** `TieredDiscount.cs:221-228`.
- **Formula:** `round(MerchantContributionPercentage + EightOrderContribution, 2) == 100`.

### Rule 5: Date window must be valid and not in the past
- **Plain language:** Start date can't be after end date; neither can already be in the past when
  the discount is created.
- **Source:** `TieredDiscount.cs:230-237` — `"Start date cannot be after end date"`,
  `"Tiered Discount Start Date cannot be in the past"`, `"Tiered Discount End Date cannot be in the past"`.
- **Also enforced independently in Application:** `AddTieredDiscountCommandValidator.cs:25-32` checks
  the same three conditions again, worded slightly differently ("...cannot be before Start Date").
  Same rule, two independent implementations — see the Conflicts section for why that matters.

### Rule 6: At least one tier, with strictly increasing minimum order values
- **Source:** `TieredDiscount.cs:239-250` — `"At least one tier is required"`,
  `"Each tier must have a unique and increasing minimum order value"` (checked by sorting the
  incoming tiers **by `MinimumOrderValue`**, not by `TierOrder` — see Open Questions).

### Rule 7: Per-tier guards
- **Plain language:** A tier's minimum order can't be negative, its discount value must be positive,
  and its order (1st/2nd/3rd) must be at least 1.
- **Source:** `TieredDiscountTier.cs:21-28` (`Create`). **Does not cap a percentage discount at
  100%** — see Conflicts.

### Rule 8: Update — name and date guards
- **Source:** `TieredDiscount.cs:171-178` (`Update`) — Arabic/English name required, end date can't
  be before start date.

### Rule 9: Reactivation blocked once expired
- **Plain language:** You can't reactivate a tiered discount whose end date has already passed —
  extend the expiry first.
- **Source:** `TieredDiscount.cs:500-503` (`Activate`) — `"Cannot activate expired tiered discount"`.
  Also independently re-checked in the Application handler:
  `UpdateTieredDiscountActivityCommand.cs:43-47` — `"Cannot reactivate an expired tieredDiscount. The expiry date has passed."`

### Rule 10: Active name uniqueness
- **Plain language:** Two *active* tiered discounts can't share the same English or Arabic name.
- **Trigger:** Create and reactivate.
- **Source:** `Shared/TalabatkApplication/TieredDiscounts/Commands/AddTieredDiscount/AddTieredDiscountCommand.cs:72-77`, `UpdateTieredDiscountActivityCommand.cs:50-55` — enforced entirely in the Application-layer handler, not in the aggregate itself.

### Rule 11: Eligibility to apply a discount to an order
- **Plain language:** A tiered discount only applies if it's active, today falls within its date
  window, it's compatible with any active item-level offer the restaurant is running, and (unless
  bypassed) the customer is on its allow-list.
- **Source:** `TieredDiscount.cs:450-474` (`ValidateTieredDiscount`) — `"Tiered discount is not active"`,
  `"Tiered discount is not valid for this date"`, `"Tiered discount cannot be used with item offers"`,
  `"Customer is not eligible for this tiered discount"`.

### Rule 12: Discount calculation
- **Plain language:** Find the highest tier the order total qualifies for; apply that tier's
  discount (percentage of the applicable restaurants' subtotal, or a fixed amount for delivery);
  cap it at `MaximumDiscountValue`; never exceed the order/delivery amount itself.
- **Source:** `TieredDiscount.cs:341-447` (`GetApplicableTier`, `CalculateDiscount`,
  `CalculateApplicableOrderAmount`).

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `TieredDiscountId` | Primary key | identity |
| `InternalCode` | Ops-facing unique code | required, unique index (`TieredDiscountMap.cs:13`), max 100 |
| `NameArabic` / `NameEnglish` | Customer-facing name | required, max 200 |
| `IsPercentage` | Percentage vs. fixed-value discount | required |
| `MaximumDiscountValue` | Cap on the discount amount | required, `decimal(18,2)` |
| `MerchantContributionPercentage` | Restaurant's share of the discount cost | required, `decimal(5,2)` — see Open Questions on precision mismatch |
| `EightOrderContribution` | 8Order's share of the discount cost | required, `decimal(18,2)` |
| `StartDate` / `EndDate` | Validity window | required |
| `AllowWithItemOffers` | Can stack with a restaurant's own item-level offer | — |
| `IsActive` | Whether it's currently usable | required |
| `AvailableToGuests` | Visible to a not-yet-logged-in guest customer | required, default `false` (`TieredDiscountMap.cs:31`) |
| `StoreTypeId` | Optional restriction to a merchant/store type | nullable FK |
| `NumberOfTimesUsed` | Usage counter, incremented/decremented via `IncreaseUsageCount`/`DecreaseUsageCount` | default `0` |
| `TieredDiscountType` | `OrderDiscount` (1) or `DeliveryDiscount` (2) | required (`TieredDiscountTypeEnum.cs`) |

## Status / State
No explicit state machine — `IsActive` (bool) plus the `StartDate`/`EndDate` window together
determine usability:

```
Created (IsActive=true/false as given)
  → Activate()     : blocked if EndDate < today  → "Cannot activate expired tiered discount"
  → Deactivate()    : always allowed, no guard
  → UpdateActivity(): re-checks expiry + active-name-uniqueness when turning ON (see Rule 9/10)
```

Independently of `IsActive`, `ValidateTieredDiscount` (Rule 11) re-derives "is this usable right
now" at apply-time from `IsActive` + the date window + item-offer compatibility + customer
eligibility — so a discount can be `IsActive=true` in the database and still be rejected at the
moment a customer tries to use it.

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `Restaurant` | Backend-Domain (legacy POCO) | Optional scoping FK, `TieredDiscountRestaurant` join | Empty list = applies to all restaurants (`CalculateApplicableOrderAmount`, `TieredDiscount.cs:436-447`). |
| `Customer` | Backend-Domain (legacy POCO) | Optional allow-list FK, `TieredDiscountCustomer` join | |
| `Audiance` (customer segment) | Backend-Domain (legacy POCO) | Optional allow-list FK, `TieredDiscountSegment` join | |
| `CustomerCart` / `CartItem` | Backend-Domain (legacy POCO) | `CartItem.TieredDiscountId` FK (`SetNull` on delete, migration `20250103000001_AddTieredDiscountIdToCartItem.cs`); `CustomerCart.LockedTieredDiscountId` (Guest Mode cart lock) | See Conflicts — delete has no usage guard. |
| `Offers` (item-level offer) | Backend-Domain (legacy POCO) | Read-only conflict check | An active, valid item offer on the same restaurant suppresses a tiered discount unless `AllowWithItemOffers=true` (`Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:99-110`). |
| Admin (`AdminUi`) | API host / Frontend (Angular) | Same `Shared/TalabatkApplication` + `Shared/TalabatkData` libraries, invoked in-process by `AdminUi/Controllers/TieredDiscountController/TieredDiscountController.cs` against the same database — no HTTP call | Admin is where campaigns are created/edited/activated/deleted. See Cross-Context Integrations below. |

## Cross-Context Integrations
| Direction | Other context | Via | Mechanism | Risk if changed |
|-----------|-----------------|-----|-----------|------------------|
| inbound (writes) | Admin | `TieredDiscountController` calls `AddTieredDiscountCommand` / `EditTieredDiscountCommand` / `UpdateTieredDiscountActivityCommand` / `DeleteTieredDiscountCommand` | Shared `TalabatkApplication`/`TalabatkData` library, own `IMediator` instance, same DB (no HTTP) | Medium — a rule change in the shared command/handler affects both Admin's write path and Customer Ordering's read path simultaneously; there is no independent contract between them to version. |

> ⚠️ **CONFLICT/GAP — Domain vs. Application, single point of enforcement**
> Neither the Domain layer (`TieredDiscountTier.Create`, `TieredDiscountTier.cs:24-25`, only checks
> `DiscountValue <= 0`) nor the Angular create form
> (`AdminUi/ClientApp/src/app/Tiered-Discount/add-tiered/add-tiered.component.ts:102-115`, tier
> value controls only have `Validators.min(1)`, no `max`) caps a **percentage** tier's discount value
> at 100%. The *only* place this is enforced is
> `AddTieredDiscountCommandValidator.cs:52-55` ("Tier X: Discount Value cannot be greater than 100%"),
> a single Application-layer validator wired into the MediatR pipeline for one specific command. If a
> future code path creates/edits a tier without going through this exact validator (a bulk import, a
> test fixture, a new admin action), nothing else stops a 150% "discount" from being saved and later
> mis-calculating `CalculateDiscount` (`TieredDiscount.cs:406-409`). This is not two sides disagreeing
> — it's one rule with exactly one line of defense across three layers that could plausibly enforce it.

> ⚠️ **CONFLICT/GAP — Delete has no usage guard**
> `Shared/TalabatkApplication/TieredDiscounts/Commands/DeleteTieredDiscount/DeleteTieredDiscountCommand.cs:24-42` hard-deletes the `TieredDiscount` row
> unconditionally — no check on `NumberOfTimesUsed`. `CartItem.TieredDiscountId` has an EF Core FK
> with `ReferentialAction.SetNull` (`Migrations/20250103000001_AddTieredDiscountIdToCartItem.cs:28`),
> so deleting a discount that has already been applied to past orders silently nulls out the
> historical attribution on those `CartItem` rows rather than failing or warning. A discount used
> hundreds of times can be deleted from the Admin UI with a single click and past reporting on "how
> much did this campaign discount" quietly loses its trail.

## Rule / Decision Matrix
| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|-----------------|---------------------|---------|--------|
| 1 | Create | merchant % + 8Order % ≠ 100 | rejected | `TieredDiscount.cs:227` |
| 2 | Create | `TieredDiscountType=DeliveryDiscount` and `IsPercentage=true` | rejected | `TieredDiscount.cs:215` |
| 3 | Create | start date < today, or end date < today, or end < start | rejected | `TieredDiscount.cs:230-237` |
| 4 | Create | tiers not unique/increasing by `MinimumOrderValue` | rejected | `TieredDiscount.cs:248-249` |
| 5 | Create (tier) | `TierOrder < 1` or `DiscountValue <= 0` or `MinimumOrderValue < 0` | rejected | `TieredDiscountTier.cs:21-28` |
| 6 | Create (Application layer only) | percentage tier `DiscountValue > 100` | rejected | `AddTieredDiscountCommandValidator.cs:52-55` |
| 7 | Create (Application layer only) | tiers 2/3 filled out of order, or non-increasing discount/min-order by `TierOrder` | rejected | `AddTieredDiscountCommandValidator.cs:65-104` |
| 8 | Activate | `EndDate < today` | rejected | `TieredDiscount.cs:500-503` |
| 9 | Create/Reactivate | another **active** discount shares the same name | rejected | `Shared/TalabatkApplication/TieredDiscounts/Commands/AddTieredDiscount/AddTieredDiscountCommand.cs:72-77`, `UpdateTieredDiscountActivityCommand.cs:50-55` |
| 10 | Apply to order | inactive, out of date range, incompatible with active item offer, or customer not eligible | rejected (no discount applied) | `TieredDiscount.cs:456-471` |
| 11 | Apply to order | order total below every tier's minimum | no discount (`GetApplicableTier` fails) | `TieredDiscount.cs:341-357` |
| 12 | Delete | discount already used (`NumberOfTimesUsed > 0`) | **no guard — proceeds anyway** | `Shared/TalabatkApplication/TieredDiscounts/Commands/DeleteTieredDiscount/DeleteTieredDiscountCommand.cs:24-42` |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 6 | `TieredDiscountTier`, `TieredDiscountRestaurant`, `TieredDiscountCustomer`, `TieredDiscountSegment` (owned children); `CartItem.TieredDiscountId`, `CustomerCart.LockedTieredDiscountId` (external FK references) |
| Sides touched | 4/5 | Backend-Domain, Backend-Application, Backend-Data, Frontend (Admin Angular) — no Legacy involvement found |
| Cross-context integrations | 1 | Admin (write path) ↔ Customer Ordering (read/apply path), same DB |
| Domain events involved | 0 | No domain event raised by this aggregate today — usage/eligibility side effects (e.g. guest-mode cart locking) are handled directly in query/command handlers, not via `PostEvent` |
| Hub? | no | Bounded to Tiered Discount feature; not referenced across unrelated features the way `Order`/`Customer` are |

## Open Questions
- [ ] `TieredDiscount.cs:245-250` sorts input tiers **by `MinimumOrderValue`** to check uniqueness/ordering, while `TierOrder` is a separate, independently-supplied field. In every code path found (`AddTieredDiscountCommandValidator`, the Angular form), the two are kept in lockstep by extra checks — but the aggregate itself never cross-validates that `TierOrder` rank matches `MinimumOrderValue` rank. Confirm this can never diverge via a path this review didn't find.
- [ ] `MerchantContributionPercentage` is mapped `decimal(5,2)` while `EightOrderContribution` is `decimal(18,2)` (`TieredDiscountMap.cs:24-25`) — both only ever need to hold 0–100, so this is likely harmless, but the inconsistency is unexplained.
- [ ] `Shared/TalabatkApplication/Commands/EditTieredDiscountCommand/EditTieredDiscountCommand.cs` is a **0-byte empty file** — appears to be a leftover from the migration to the newer `TieredDiscounts/Commands/EditTieredDiscount/` folder convention. Confirm it's safe to delete; not removed by this review since deleting code isn't this skill's job.
- [ ] The legacy `Commands/EditTieredDiscountCommand` **folder name** still exists (now empty) alongside the current `TieredDiscounts/Queries/GetVoucherByIdQuery/GetTieredDiscountByIdQuery.cs` — a folder literally named after Vouchers holding a Tiered Discount query. Likely copy-pasted from a Voucher feature; worth a rename, not attempted here.
- [ ] Admin context (`AdminUi`) itself is not yet documented by this skill — only its integration point with `TieredDiscount` is recorded here and in `_system/_integrations.md`.
- [ ] `TieredDiscountAggregate/POCOs/TieredDiscountTierPoco.cs` was not read in this pass; assumed to be a plain input DTO mirroring `TierDto` based on usage in `TieredDiscount.Create`.

## Related
- Business view: [[TieredDiscount.business|TieredDiscount]]
- [[TieredDiscountTier|TieredDiscountTier & other children]] — tiers, restaurant/customer/segment allow-lists
- Business-term background: [[../../../../../Talabatk.IDS/CONTEXT|Customer Ordering CONTEXT.md]] (Discounts & coupons section) — CONTEXT.md's Guest Mode section calls guest-mode "not implemented yet", but the migration history (`20260715150740_GuestModeCart.cs`, `MergeGuestCartIntoCustomerCommand.cs`, `CustomerCartLockedDiscountTests.cs`) shows it has since shipped, including the `CustomerCart.LockedTieredDiscountId` retention behavior this note depends on (see `GetCustomerTieredDiscountQuery.cs:81-135`). **CONTEXT.md is stale on this point** — worth flagging to whoever owns it.
