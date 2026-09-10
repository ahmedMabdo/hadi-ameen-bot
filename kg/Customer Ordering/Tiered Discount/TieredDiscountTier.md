---
id: 8orders/customer-ordering/tiered-discount/tiereddiscounttier
note_type: single
rule_count: 5
context: Customer Ordering
feature: Tiered Discount
entity: TieredDiscountTier
entity_type: child
covers: [TieredDiscountCustomer, TieredDiscountRestaurant, TieredDiscountSegment]
sources:
  - path: Shared/TalabatkData/Mapping/TieredDiscountConfigurations/TieredDiscountTierMap.cs
    sha1: 5155e83ed54f
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscount.cs
    sha1: 5a01e502c2ef
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountCustomer.cs
    sha1: deb76b9a48a6
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountRestaurant.cs
    sha1: 05919a5d9b9e
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountSegment.cs
    sha1: 7faef991f603
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs
    sha1: 3a2304c31451
last_updated: 2026-08-23
tags: [customer-ordering, tiered-discount, child, technical, backend-domain]
---
# TieredDiscountTier, TieredDiscountRestaurant, TieredDiscountCustomer, TieredDiscountSegment

Four small child entities owned by [[TieredDiscount.technical|TieredDiscount]], all
under `Shared/TalabatkLogic/TieredDiscountAggregate/`. Grouped into one note since each is a thin
join/value record with no independent lifecycle.

## TieredDiscountTier — `TieredDiscountTier.cs`
The actual spend threshold + reward. One `TieredDiscount` has 1–3 tiers (in every code path seen —
the Domain layer itself doesn't cap the count, only the Admin Angular form and its accompanying
`AddTieredDiscountCommandValidator` assume up to 3, labelled 1st/2nd/3rd).

| Field | Meaning | Constraints |
|-------|---------|-------------|
| `TieredDiscountTierId` | PK | identity |
| `TieredDiscountId` | Owning discount | FK |
| `MinimumOrderValue` | Spend threshold to unlock this tier | `decimal(18,2)`, ≥ 0, must be unique+increasing across a discount's tiers |
| `DiscountValue` | The reward — a percent or a fixed amount depending on the parent's `IsPercentage` | `decimal(18,2)`, > 0. **Not capped at 100 even when percentage** at the Domain level — see the parent's Conflicts section |
| `TierOrder` | Display rank (1st/2nd/3rd) | ≥ 1; unique per discount (`TieredDiscountTierMap.cs:12`, unique index on `(TieredDiscountId, TierOrder)`) |

Business rule citations: `TieredDiscountTier.cs:21-28` (`Create` — the three guards above),
`TieredDiscountTier.cs:40-51` (`Update` — same min-order/discount-value guards, no upper bound).

## TieredDiscountRestaurant — `TieredDiscountRestaurant.cs`
Optional scoping: which restaurant(s) the discount applies to. No rows = applies to every
restaurant (`TieredDiscount.cs:436-447`, `CalculateApplicableOrderAmount`). Just a
`(TieredDiscountRestaurantId, TieredDiscountId, RestaurantId)` join row, no rules of its own.

## TieredDiscountCustomer — `TieredDiscountCustomer.cs`
Optional customer allow-list. No rows = no direct-customer restriction (still gated by segment or
guest-visibility rules on the parent). `(TieredDiscountCustomerId, TieredDiscountId, CustomerId)`.

## TieredDiscountSegment — `TieredDiscountSegment.cs`
Optional audience/segment allow-list — links to `Audiance` (the existing customer-segmentation
entity used elsewhere in the codebase, e.g. Loyalty). `(TieredDiscountSegmentId, TieredDiscountId, SegmentId)`.
This is the exact mechanism `TalabatkAPIs/CONTEXT.md` (Discounts & coupons → "Target audience /
segment") already documents: a guest can see and lock in a segment-restricted discount their real
account wouldn't otherwise qualify for once logged in, and this is a **known, deliberate, ops-owned
tradeoff, not a bug** — see `TalabatkAPIs/docs/adr/0002-no-guardrail-segment-restricted-guest-discount.md`.
Do not "fix" this as a side effect of touching this entity; it's an intentional decision.

## Rule / Decision Matrix

One threshold in a "spend more, save more" campaign. Small, and one of the few entities in the codebase whose every guard is a business rule rather than a null check.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | Minimum order value cannot be negative | `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs:22` |  |
| 2 | Discount value must be greater than zero | `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs:25` | A tier that discounts nothing cannot exist |
| 3 | Tier order must be at least 1 | `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs:28` | So the tiers are always orderable from 1 |
| 4 | `Update` re-checks the two value rules | `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs:43-46` | But **not** the tier order — that is create-only |
| 5 | `Create` returns `Result<TieredDiscountTier>`; the private constructor makes it the only way in | `Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs:19` | Part of a real aggregate, and it shows |

> What no tier can check is the relationship **between** tiers: nothing here prevents tier 2 having a
> lower minimum than tier 1, or two tiers sharing an order. That invariant belongs to
> [[TieredDiscount.technical|the aggregate root]], and is the reason the root exists.

## Related
- [[TieredDiscount.technical|TieredDiscount]] — the parent aggregate and its rules.
- [[TieredDiscount.business|TieredDiscount (business)]]
