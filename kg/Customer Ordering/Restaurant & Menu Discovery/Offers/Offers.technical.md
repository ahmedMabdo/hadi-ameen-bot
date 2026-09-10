---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/offers-technical
note_type: technical
rule_count: 5
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: Offers
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/OfferItem.cs
    sha1: a4a74acaf721
  - path: Shared/TalabatkLogic/TalabatkModels/Offers.cs
    sha1: 5088c83f964e
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, transactional, technical, backend-domain]
---
# Offers (+ OfferItem) — Technical

> **Layer:** Backend-Domain — legacy entity, richer than anemic (validated `Instance`, several
> behavior methods), no private constructor.
> **Context:** Customer Ordering (menu-item promotions, distinct from Discounts & Coupons'
> PromoCodes/Vouchers and Tiered Discount).
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Offers.cs` / `OfferItem.cs`
> **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Creation validates several fields; `UpdateRestaurantOffer` validates none of them
- **Source:** `Offers.cs:109-178` (`Instance`) — `offerWeekDays` non-blank; if
  `applyOfferMaximumDiscount` is on, `maximumDiscountPerOffer > 0`; `minimumOrderTotal >= 0`; at least
  2 descriptions; at least 1 offer item. `UpdateRestaurantOffer` (`:199-227`) reassigns every one of
  these same fields with **zero** guards — the same create-validates/update-doesn't asymmetry already
  confirmed multiple times elsewhere in this pass (`DeliveryZone`, `DeliverySupplier`,
  `Configuration`'s bulk-update methods).

### Rule 2: ⚠️ Likely bug — `Instance` assumes an Arabic description exists without checking
- **Plain language:** Creating an offer only checks that at least two descriptions were provided, not
  that one of them is actually in Arabic — but the code immediately assumes one is.
- **Source:** `Offers.cs:165` —
  `ReferenceOfferDescriptions = offersDescriptions.FirstOrDefault(x => x.LanguageId ==
  (int)Language.Arabic).OfferDescriptions` — if no Arabic-language description is in the list,
  `FirstOrDefault` returns `null` and the immediate `.OfferDescriptions` access throws
  `NullReferenceException`. The `offersDescriptions.Count < 2` guard three lines earlier doesn't
  guarantee *which* languages are present.

### Rule 3: Two independent, overlapping "is this offer currently valid" checks
- **Plain language:** There are two separate methods that both answer "is this offer active right
  now", with different scope and different overnight-window logic — a caller has to know which one to
  use, and a future change to one might not be mirrored in the other.
- **`CheckOfferIsValid(nowDate)`** (`:46-106`) — checks only the time-of-day window (`StartTime`/
  `EndTime`), with three explicit branches for same-day vs. overnight-crossing (before/after
  midnight) windows. Does **not** check `OfferWeekDays` or the offer's date range at all.
- **`ValidateOfferWithinDatesAndWorkingDays(...)`** (`:239-290`) — checks the offer's date range,
  **and** whether today's day-of-week is in `OfferWeekDays`, **and** the time window (its own,
  differently-structured overnight-crossing logic using `previousDayStart`/`nextDayEnd` rather than
  `CheckOfferIsValid`'s three-way branch).
- Not confirmed which callers use which, or whether `CheckOfferIsValid` is dead/superseded code —
  flagged as an Open Question, but the shape matches the repo's other confirmed "same rule, two
  implementations" findings (`_conflicts.md` #8, #10, #18).

### Rule 4: `RemoveOfferItem()` is an empty stub
- **Source:** `Offers.cs:234-237` — the method body is empty. Either dead/unfinished code, or item
  removal happens some other way (direct collection manipulation at the Application layer) not
  routed through this method — not traced.

### Rule 5 (OfferItem): ⚠️ Confirmed bug — `UpdateOfeerItem` self-assigns 4 of its 6 fields, silently ignoring its own parameters
- **Plain language:** Most of what looks like an "update" method doesn't actually use the values
  passed into it — it reassigns several fields to their own current value instead.
- **Source:** `OfferItem.cs:81-93` —
  ```
  this.IsActive = IsActive;              // self-assignment: property IsActive, not parameter isActive
  this.IsPercentage = IsPercentage;      // same issue
  this.Discount = discount;              // correct — parameter discount, lowercase, distinct name
  this.MenuItemPriceId = MenuItemPriceId; // self-assignment: property, not parameter menuItemPriceId
  this.ExtraItemId = ExtraItemId;        // self-assignment: property, not parameter extraItemId
  this.Order = order;                     // correct
  ```
  Because C# is case-sensitive, `IsActive` (capital, the property) and `isActive` (lowercase, the
  parameter) are different identifiers — the property-cased right-hand sides silently reference the
  entity's own current value rather than the incoming argument. Confirms and precisely locates a
  previously informal finding ("case-sensitivity self-assignment bug that makes most of the method a
  no-op") — exactly `IsActive`, `IsPercentage`, `MenuItemPriceId`, `ExtraItemId` are affected;
  `Discount` and `Order` are not (their parameter names don't collide case-insensitively in the same
  way — `discount`/`Discount` and `order`/`Order` still differ only by case, but the code happens to
  reference the correct lowercase side for those two).
- **Contrast:** `UpdateOfferId(offerId)` (`:107-114`) is correctly written, with an early-return guard
  against a redundant reassignment of the same value.

## Key Fields (Offers)
| Field | Meaning |
|-------|---------|
| `MerchantContributionPercentage` / `_8OrdersContributionPercentage` (computed `100 - Merchant%`) | Discount cost split |
| `OfferWeekDays` | Which days of the week the offer runs, stored as a delimited string of day-of-week ints |
| `MaximumDiscountPerOffer` / `ApplyOfferMaximumDiscount` | Optional per-order discount cap |
| `TA_OfferItem` | The discounted menu-item-price lines (`OfferItem`) |

## Related
- Business view: [[Offers.business|Offers]]
- [[MenuItem.technical|MenuItem]] — `OfferItem.MenuItemPriceId` targets a specific `MenuItemPrice`

## Open Questions
- [ ] Which callers use `CheckOfferIsValid` vs. `ValidateOfferWithinDatesAndWorkingDays` (Rule 3) —
  not traced to the Application layer.
- [ ] Whether `RemoveOfferItem`'s empty body (Rule 4) is dead code or item removal happens elsewhere.
- [ ] Whether the missing-Arabic-description crash (Rule 2) has ever been hit in practice.
- [ ] `OffersDescriptions` itself not opened in full (assumed to be a simple language/text pair,
  matching the shape of other `*Description` entities in this pass).
