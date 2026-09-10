---
id: 8orders/customer-ordering/tiered-discount/scenarios
title: Tiered Discount — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Tiered Discount
audience: Business · QA · Developer
sources:
  - path: AdminUi/ClientApp/src/app/Tiered-Discount/add-tiered/add-tiered.component.ts
    sha1: 043ba9fc322f
  - path: Shared/TalabatkApplication/TieredDiscounts/Commands/AddTieredDiscount/AddTieredDiscountCommandValidator.cs
    sha1: 03a1019d9766
  - path: Shared/TalabatkApplication/TieredDiscounts/Commands/UpdateTieredDiscountActivityCommand/UpdateTieredDiscountActivityCommand.cs
    sha1: a9cd6bb31d01
  - path: Shared/TalabatkData/Migrations/20250103000001_AddTieredDiscountIdToCartItem.cs
    sha1: eea62e123801
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscount.cs
    sha1: 5a01e502c2ef
  - path: Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscountTier.cs
    sha1: 3a2304c31451
last_updated: 2026-08-02
---
# Tiered Discount — Scenario Catalog

> Every meaningful behavior of the feature as precondition → action → expected outcome, with the
> rule(s) it exercises. Use this to answer "what happens if…" and to scope regression on a change.

## Happy path
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| H1 | Campaign active, valid dates, no conflicting offer | Ops creates a campaign with 3 tiers, 60/40 restaurant/8Order split | Campaign created | `TieredDiscount.cs:191-253` |
| H2 | Active campaign, guest-visible, customer cart total ≥ Tier 1 minimum | Guest checks out at the eligible restaurant | Tier 1 discount applied to order | `TieredDiscount.cs:341-357`, `378-431` |
| H3 | Same as H2, cart total ≥ Tier 3 minimum | Guest checks out | Highest qualifying tier (Tier 3) applied, capped at `MaximumDiscountValue` | `TieredDiscount.cs:392-419` |
| H4 | Campaign is `DeliveryDiscount` type | Customer qualifies | Fixed amount (never percentage) taken off the delivery fee, capped at both `MaximumDiscountValue` and the original delivery fee | `TieredDiscount.cs:420-428` |

## Partial / incremental
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| P1 | Cart total below Tier 1 minimum | Customer views restaurant | "Add items worth X to get Y% off" progress message shown for the next tier | `TieredDiscount.cs:360-375`, `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:265-333` |
| P2 | Cart total between Tier 1 and Tier 2 minimums | Customer views restaurant | Message shown for Tier 2 as the next unlockable reward | same as P1 |
| P3 | Ops edits a campaign's name/description/expiry/targeting mid-run via `EditTieredDiscount` | — | Tiers themselves are unaffected — `EditTieredDiscount` (`EditTieredDiscountCommand.cs`) never touches `TieredDiscountTiers` | `TieredDiscount.cs:271-326` (`UpdateV1`) |

## Negative / guard
| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|--------------|--------|--------------------------------|-----------------|
| N1 | — | Ops creates a campaign where merchant % + 8Order % ≠ 100 | Rejected — "Sum of Merchant and 8Order contribution percentages must equal 100%" | `TieredDiscount.cs:227-228` |
| N2 | — | Ops creates a `DeliveryDiscount` campaign with `IsPercentage=true` | Rejected — "Delivery discount can only be fixed value" | `TieredDiscount.cs:215-216` |
| N3 | — | Ops sets a start or end date in the past | Rejected (checked twice, independently, in Domain and Application) | `TieredDiscount.cs:233-237`, `AddTieredDiscountCommandValidator.cs:25-29` |
| N4 | Tier 2 filled without Tier 1 | Ops submits the create form | Rejected — "Tier 1 must be completed before entering Tier 2 data" (checked in Angular form, again in `AddTieredDiscountCommandValidator`) | `add-tiered.component.ts:865-893`, `AddTieredDiscountCommandValidator.cs:65-76` |
| N5 | Existing active campaign named "Ramadan Offer" | Ops creates/reactivates another campaign named "Ramadan Offer" | Rejected — "...name already exists" | `Shared/TalabatkApplication/TieredDiscounts/Commands/AddTieredDiscount/AddTieredDiscountCommand.cs:72-77`, `UpdateTieredDiscountActivityCommand.cs:50-55` |
| N6 | Campaign `EndDate` already passed, currently inactive | Ops reactivates it | Rejected — "Cannot activate expired..." / "Cannot reactivate an expired..." | `TieredDiscount.cs:500-503`, `UpdateTieredDiscountActivityCommand.cs:43-47` |
| N7 | Customer not on the campaign's customer/segment allow-list, campaign is not guest-visible or customer is not a guest | Customer checks out at an eligible restaurant | No discount applied (silently — not surfaced as an error to the customer) | `TieredDiscount.cs:465-471` |
| N8 | Restaurant has an active, valid item offer; campaign `AllowWithItemOffers=false` | Customer checks out | Tiered discount suppressed in favor of/alongside the item offer rules | `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:99-110`, `TieredDiscount.cs:462-463` |
| N9 | **Not enforced at the Domain or Frontend layer** — percentage tier value > 100 | A path other than `AddTieredDiscountCommand` creates/edits a tier | **Not rejected** — see the flagged conflict in `TieredDiscount.technical.md` | `TieredDiscountTier.cs:24-25` (gap) |

## Returns / cancellation / reversal
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| R1 | Order using a tiered discount is cancelled/reversed | `DecreaseUsageCount()` called | `NumberOfTimesUsed` decremented (floored at 0) | `TieredDiscount.cs:483-490` |
| R2 | Campaign has `NumberOfTimesUsed > 0` | Ops deletes the campaign | **No guard — deletion proceeds**; `CartItem.TieredDiscountId` on past orders is set to `NULL` (FK `SetNull`), losing historical attribution | `Shared/TalabatkApplication/TieredDiscounts/Commands/DeleteTieredDiscount/DeleteTieredDiscountCommand.cs:24-42`, migration `20250103000001_AddTieredDiscountIdToCartItem.cs:22-28` — flagged conflict |

## Integration (cross-side / cross-context)
| # | Precondition | Action | Expected outcome | Rule / source |
|---|--------------|--------|--------------------|-----------------|
| I1 | Guest builds a cart and a tiered discount is locked to it | Guest completes OTP login (promote/merge) | The locked discount is retained on the cart and shown again, bypassing normal customer/segment eligibility, but still checked against active/date/offer rules for that merchant | `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:81-135` |
| I2 | Ops creates/edits/deletes a campaign in `AdminUi` | Customer immediately queries `GetCustomerTieredDiscountQuery` in `TalabatkAPIs` | Change is visible immediately — both hosts read/write the same database through the same shared Application/Data code, no cache or sync delay | `_system/_integrations.md` row 7 |

## Open Questions
- [ ] No scenario found yet for what a customer sees if the same order total qualifies for a tier
  under **two** applicable campaigns targeting the same restaurant simultaneously — the query only
  ever selects a single best match (`OrderByDescending(td => td.MaximumDiscountValue)`,
  `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:168-170`); confirm this is the intended tie-break and
  not just an artifact of ordering.
- [ ] No test or code path found confirming what happens if a percentage tier discount **is** saved
  above 100% through some path other than `AddTieredDiscountCommand` (see N9) — worth a deliberate
  test if this is a real risk the team wants closed.
