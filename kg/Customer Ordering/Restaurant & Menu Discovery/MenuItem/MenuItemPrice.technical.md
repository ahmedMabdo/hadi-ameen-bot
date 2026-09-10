---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/menuitemprice-technical
note_type: technical
rule_count: 7
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: MenuItemPrice
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/ImportExcel/ImportExcelCommand.cs
    sha1: 3202bce15d85
  - path: Shared/TalabatkApplication/Commands/ManageOptionGroupsFromExcelCommand/ManageOptionGroupsFromExcelCommand.cs
    sha1: 17e58ef92597
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemPrice.cs
    sha1: da50ed44127b
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, transactional, technical, backend-domain]
---
# MenuItemPrice — Technical

> **Layer:** Backend-Domain — legacy entity extending `AuditableEntity` (built-in change-tracking via
> `TrackChange(...)`), event-raising, richer than most entities in this pass.
> **Context:** Customer Ordering (child of [[MenuItem.technical|MenuItem]] — a menu item's price
> tier, e.g. "Small"/"Large").
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/MenuItemPrice.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Three separate construction paths with inconsistent validation
- **Plain language:** There's a plain constructor, a second constructor, and a static factory — none
  of the three actually validate their inputs, which is the opposite of most entities in this pass
  (where at least *creation* validates something).
- **Source:** the parameterless constructor (`:15-22`), the 4-arg constructor
  (`:24-35`, sets `Available = true` directly, bypassing several fields the static factory sets), and
  `Instance(...)` (`:61-95`) — **none** check `price >= 0`, `priceReferenceName` non-blank, or
  anything else.
- **⚠️ Contrast — `Update` validates where `Instance` doesn't:** `Update(...)` (`:475-582`) rejects a
  blank `priceReferenceName` (`:488-491`) — the inverse of the repo's more common "create validates,
  update doesn't" shape (`DeliveryZone`, `DeliverySupplier`, `Offers`, `Configuration`) — here it's
  create that skips validation and update that has it.

### Rule 2: Every field change is tracked via `TrackChange`, but all tagged with the same `EntityChangeType.Size`
- **Plain language:** This entity has real audit logging built in — every price, availability, name,
  and quantity-limit change is recorded with before/after values — but every single one of those
  audit entries is tagged with the same change-type category, regardless of what actually changed.
- **Source:** every `TrackChange(...)` call in the file (`UpdatePriceQuantityLimits` `:106-121`,
  `UpdatePriceReferenceName` `:135-141`, `UpdatePrice` `:153-159`, `UpdateExcelData` `:414-429`,
  `Activate`/`DeActivate` `:442-448`/`:459-465`, `Update` `:493-551`) passes
  `(int)EntityChangeType.Size` as the change-type argument — for a price change, a name change, an
  availability toggle, *and* a quantity-limit change alike. Either `EntityChangeType.Size` is a
  generic catch-all category (not confirmed — the enum's other values weren't opened in this pass),
  or this is a copy-paste artifact that mislabels most of this entity's audit trail by change type.

### Rule 3: Price changes raise a domain event only when the value actually changes; deferred until the entity has a real id
- **Source:** `UpdatePrice` (`:151-178`) and `Update` (`:567-575`) both compare `oldPrice != newPrice`
  before raising `ChangeCartItemPriceEvent` — presumably what keeps a cart's snapshotted price in sync
  (see [[CartItem\|CartItem]]'s `PriceChanged` flag in Customer Ordering's Cart & Checkout). Every
  mutator additionally guards `if (this.MenuItemPriceId != 0)` before calling
  `AddRecordPostDomainEvent()` — the same "wait until EF assigns a real id" deferred-event pattern
  seen on `Compensation.RaisePendingCompensationApprovedEventAfterPersist` elsewhere in this pass.

### Rule 4: Two near-duplicate offer-discount calculations
- **Plain language:** There are two methods that compute the exact same percentage-or-fixed discount
  formula, one that looks the offer up by id and one that takes an already-resolved offer directly.
- **Source:** `CalculateOfferDiscount(offerid)` (`:180-201`, looks up `OfferItem` by `OfferId`) and
  `CalculateDiscountForOfferItem(OfferItem offer)` (`:202-222`, takes the offer directly) — both
  compute `offer.IsPercentage ? (offer.Discount * Price / 100) : offer.Discount`, rounded to 2
  decimals. Same "same rule, two implementations" shape already confirmed multiple times in this pass
  (`_conflicts.md` #8, #10, #18, #22).

### Rule 5: Option-group templating is a real 3-way diff (add/update/remove)
- **Plain language:** When a price tier's option groups (e.g. size/topping choices) are set from a
  template, the system reconciles the incoming template against what's already there — removing
  groups no longer in the template, adding new ones, and syncing individual options within groups
  that still match.
- **Source:** `ApplyOptionGroupsTemplate` (`:308-315`) calls, in order: `UpdateMatchingGroups`
  (`:360-398` — for each group matched by `OptionGroupId`, removes options no longer present and adds
  options newly present, matched by `OptionGroupItemId`), `RemoveDeletedOptionGroups` (`:400-410`),
  `AddNewOptionGroups` (`:317-358`). A reasonably sophisticated reconciliation for what's otherwise a
  fairly anemic entity.

### Rule 6: Application layer — `ImportExcelCommand` skips row validation entirely, unlike its preview sibling
- **⚠️ Confirmed bug:** `ImportExcelCommand` (the actual commit path for a restaurant's bulk Excel
  price/availability update, calling `UpdateExcelData` above) throws an unguarded
  `NullReferenceException` on `xor.StartsWith('_')` if any row's `Sku` is `null` — no per-row validation
  at all before changes are applied.
- **Contrast:** its sibling `PreviewPriceUpdateFromExcelCommand` (dry-run preview of the same import)
  validates every row via `ValidateRowAsync` and reports per-row errors instead of crashing — the
  actual commit path skips that same safety net entirely.
- **Source:** `ImportExcelCommand.cs:38-50`.

### Rule 7: Application layer — Excel option-group import creates duplicate options on re-upload
- **⚠️ Confirmed bug:** `ManageOptionGroupsFromExcelCommand.AddNewOptionsToExistingGroup` (the "add"
  side of the Rule 5 template layer, invoked when an Excel-imported group name matches an existing
  `MenuItemOptionGroup`) looks up `existingOption` by `OptionReferenceName` but never checks the
  result before unconditionally calling `CreateOptionItem` — so re-uploading the same Excel sheet
  against a group that already has that option creates a **duplicate** `MenuItem`/
  `MenuItemOptionGroupItem` every time, instead of updating or skipping it.
- **Contrast:** the sibling *update* command, `UpdateOptionGroupsFromExcelCommand`, does this
  correctly — it matches existing items by `OptionGroupItemId` and calls `.Update(...)`.
- **Source:** `ManageOptionGroupsFromExcelCommand.cs:180-192`.

## Key Fields
| Field | Meaning |
|-------|---------|
| `MaximumQuantityPerOrder` / `MaximumQuantityPerDay` | Purchase limits, resettable via `ResetMaxQuantityLimits()` |
| `ResetMaxQuantityAfterOfferEnd` | Whether the above limits auto-reset once a related offer ends — the reset trigger itself wasn't traced in this pass |
| `Available` | Toggled via `Activate()`/`DeActivate()`, both audit-tracked (Rule 2) |
| `DeliveryBoxUnitSizeId` | Ties to `DeliveryBoxUnitSize` (not opened in this pass) — presumably packaging/box-count for delivery |

## Related
- [[MenuItem.technical|MenuItem]] — owning entity (browsing-slice documented; this note extends coverage rather than duplicating)
- [[CartItem|CartItem]] — snapshots price at add-time; `ChangeCartItemPriceEvent` (Rule 3) is what keeps it able to detect drift

## Open Questions
- [ ] Whether `EntityChangeType.Size` (Rule 2) is genuinely a catch-all category or a mislabeling bug — the enum's other values weren't opened.
- [ ] What triggers the `ResetMaxQuantityAfterOfferEnd` reset — not traced to a caller.
- [ ] `MenuItemPriceSku`, `DeliveryBoxUnitSize` not opened in full.
